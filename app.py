import os
import csv
import io
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, Response, abort
)
from models import db, User, Vehicle, FuelLog, ServiceRecord, Reminder, SecurityLog
from security import (
    login_required, get_current_user, get_active_vehicle,
    verify_vehicle_ownership, log_security_event, validate_password_strength
)

# App Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'autovault-secure-key-3rd-sem-cybersecurity-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///autovault.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cookie & Session Security (Cyber Security hardening)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static asset caching in browser

db.init_app(app)

# Global Context Processor for Templates
@app.context_processor
def inject_global_vars():
    user = get_current_user()
    active_vehicle = get_active_vehicle(user) if user else None
    
    # Calculate overdue / due soon reminders count for badge
    pending_alerts_count = 0
    if active_vehicle:
        for r in active_vehicle.reminders:
            if not r.is_completed and r.get_status(active_vehicle.current_odometer) in ['Overdue', 'Due Soon']:
                pending_alerts_count += 1

    return {
        'current_user': user,
        'active_vehicle': active_vehicle,
        'user_vehicles': user.vehicles if user else [],
        'pending_alerts_count': pending_alerts_count,
        'now_year': datetime.now().year
    }


# ----------------------------------------------------
# AUTHENTICATION ROUTES
# ----------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validations
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Cyber Security: Password strength check
        is_strong, msg = validate_password_strength(password)
        if not is_strong:
            flash(msg, 'warning')
            return render_template('auth/register.html', username=username, email=email)

        # Check existing user
        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose another.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        if User.query.filter_by(email=email).first():
            flash('Email is already registered. Please log in.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Create user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Audit Log
        log_security_event('REGISTER', f'New account registered: {username}', user_id=new_user.id)

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash('Please enter both your username/email and password.', 'danger')
            return render_template('auth/login.html', identifier=identifier)

        # Support login via either username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            # Regenerate session (Session Fixation defense)
            session.clear()
            session['user_id'] = user.id
            session.permanent = True

            # Set default active vehicle
            if user.vehicles:
                session['active_vehicle_id'] = user.vehicles[0].id

            log_security_event('LOGIN_SUCCESS', f'User {user.username} logged in successfully', user_id=user.id)
            flash(f'Welcome back, {user.username}!', 'success')

            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('dashboard'))
        else:
            user_id = user.id if user else None
            log_security_event('LOGIN_FAILED', f'Failed login attempt for identifier: {identifier}', user_id=user_id)
            flash('Invalid username/email or password.', 'danger')
            return render_template('auth/login.html', identifier=identifier)

    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_security_event('LOGOUT', 'User logged out', user_id=user_id)
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('login'))


# ----------------------------------------------------
# VEHICLE SWITCHER & MANAGEMENT
# ----------------------------------------------------
@app.route('/vehicles/select/<int:vehicle_id>')
@login_required
def select_vehicle(vehicle_id):
    user = get_current_user()
    vehicle = verify_vehicle_ownership(vehicle_id, user.id)
    session['active_vehicle_id'] = vehicle.id
    flash(f'Switched active vehicle to {vehicle.make} {vehicle.model} ({vehicle.license_plate}).', 'info')
    
    # Return to previous page or dashboard
    referer = request.headers.get('Referer')
    if referer and request.host in referer:
        return redirect(referer)
    return redirect(url_for('dashboard'))


@app.route('/vehicles', methods=['GET', 'POST'])
@login_required
def vehicles():
    user = get_current_user()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        make = request.form.get('make', '').strip()
        model = request.form.get('model', '').strip()
        year = request.form.get('year', type=int)
        license_plate = request.form.get('license_plate', '').strip().upper()
        fuel_type = request.form.get('fuel_type', 'Petrol')
        odometer = request.form.get('current_odometer', type=float) or 0.0
        purchase_date_str = request.form.get('purchase_date', '')

        if not name or not make or not model or not year or not license_plate:
            flash('Please complete all required vehicle fields.', 'danger')
            return redirect(url_for('vehicles'))

        purchase_date = None
        if purchase_date_str:
            try:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        vehicle = Vehicle(
            user_id=user.id,
            name=name,
            make=make,
            model=model,
            year=year,
            license_plate=license_plate,
            fuel_type=fuel_type,
            current_odometer=odometer,
            purchase_date=purchase_date
        )
        db.session.add(vehicle)
        db.session.commit()

        # Set as active vehicle
        session['active_vehicle_id'] = vehicle.id

        log_security_event('VEHICLE_ADD', f'Added vehicle: {make} {model} ({license_plate})', user_id=user.id)
        flash(f'Vehicle "{name}" added successfully!', 'success')
        return redirect(url_for('vehicles'))

    all_vehicles = Vehicle.query.filter_by(user_id=user.id).all()
    return render_template('vehicles/index.html', vehicles=all_vehicles)


@app.route('/vehicles/edit/<int:vehicle_id>', methods=['POST'])
@login_required
def edit_vehicle(vehicle_id):
    user = get_current_user()
    vehicle = verify_vehicle_ownership(vehicle_id, user.id)

    vehicle.name = request.form.get('name', vehicle.name).strip()
    vehicle.make = request.form.get('make', vehicle.make).strip()
    vehicle.model = request.form.get('model', vehicle.model).strip()
    vehicle.year = request.form.get('year', vehicle.year, type=int)
    vehicle.license_plate = request.form.get('license_plate', vehicle.license_plate).strip().upper()
    vehicle.fuel_type = request.form.get('fuel_type', vehicle.fuel_type)
    
    new_odo = request.form.get('current_odometer', type=float)
    if new_odo is not None and new_odo >= 0:
        vehicle.current_odometer = new_odo

    purchase_date_str = request.form.get('purchase_date', '')
    if purchase_date_str:
        try:
            vehicle.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    db.session.commit()
    log_security_event('VEHICLE_UPDATE', f'Updated vehicle: {vehicle.license_plate}', user_id=user.id)
    flash(f'Vehicle "{vehicle.name}" updated successfully.', 'success')
    return redirect(url_for('vehicles'))


@app.route('/vehicles/delete/<int:vehicle_id>', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    user = get_current_user()
    vehicle = verify_vehicle_ownership(vehicle_id, user.id)

    plate = vehicle.license_plate
    db.session.delete(vehicle)
    db.session.commit()

    if session.get('active_vehicle_id') == vehicle_id:
        session.pop('active_vehicle_id', None)

    log_security_event('VEHICLE_DELETE', f'Deleted vehicle: {plate}', user_id=user.id)
    flash(f'Vehicle {plate} and all its associated logs were deleted.', 'info')
    return redirect(url_for('vehicles'))


# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    if not user.vehicles:
        flash('Welcome to AutoVault! Let\'s begin by adding your first vehicle.', 'info')
        return redirect(url_for('vehicles'))

    vehicle = get_active_vehicle(user)
    if not vehicle:
        return redirect(url_for('vehicles'))

    # Recent fuel logs (top 5)
    recent_fuel_logs = FuelLog.query.filter_by(vehicle_id=vehicle.id).order_by(FuelLog.odometer.desc()).limit(5).all()

    # Recent service records (top 5)
    recent_service_records = ServiceRecord.query.filter_by(vehicle_id=vehicle.id).order_by(ServiceRecord.date.desc()).limit(5).all()

    # Reminders with active status
    reminders = Reminder.query.filter_by(vehicle_id=vehicle.id, is_completed=False).all()
    overdue_or_soon_reminders = [
        r for r in reminders if r.get_status(vehicle.current_odometer) in ['Overdue', 'Due Soon']
    ]

    # Current month fuel expense
    current_year = date.today().year
    current_month = date.today().month
    monthly_fuel_expense = sum(
        log.total_cost for log in vehicle.fuel_logs
        if log.date.year == current_year and log.date.month == current_month
    )

    # Mileage threshold warning check
    # If the latest calculated mileage is unusually low (< 12 km/L for cars or < 25 km/L for bikes)
    latest_mileage_log = next((l for l in vehicle.fuel_logs if l.mileage and l.mileage > 0), None)
    low_mileage_warning = False
    if latest_mileage_log:
        threshold = 28.0 if 'bike' in vehicle.name.lower() or 'motor' in vehicle.name.lower() else 11.5
        if latest_mileage_log.mileage < threshold:
            low_mileage_warning = True

    return render_template(
        'dashboard.html',
        vehicle=vehicle,
        recent_fuel_logs=recent_fuel_logs,
        recent_service_records=recent_service_records,
        active_reminders=overdue_or_soon_reminders,
        monthly_fuel_expense=monthly_fuel_expense,
        latest_mileage_log=latest_mileage_log,
        low_mileage_warning=low_mileage_warning
    )


# ----------------------------------------------------
# FUEL TRACKER ROUTES
# ----------------------------------------------------
@app.route('/fuel')
@login_required
def fuel_index():
    user = get_current_user()
    if not user.vehicles:
        flash('Please add a vehicle first.', 'warning')
        return redirect(url_for('vehicles'))

    vehicle = get_active_vehicle(user)
    logs = FuelLog.query.filter_by(vehicle_id=vehicle.id).order_by(FuelLog.odometer.desc()).all()
    return render_template('fuel/index.html', vehicle=vehicle, logs=logs)


@app.route('/fuel/add', methods=['POST'])
@login_required
def add_fuel_log():
    user = get_current_user()
    vehicle = get_active_vehicle(user)
    if not vehicle:
        flash('No vehicle selected.', 'danger')
        return redirect(url_for('vehicles'))

    date_str = request.form.get('date')
    odometer = request.form.get('odometer', type=float)
    fuel_amount = request.form.get('fuel_amount', type=float)
    fuel_price = request.form.get('fuel_price', type=float)
    is_full_tank = bool(request.form.get('is_full_tank'))
    notes = request.form.get('notes', '').strip()

    if not date_str or odometer is None or fuel_amount is None or fuel_price is None:
        flash('Please fill in all required fuel log fields.', 'danger')
        return redirect(url_for('fuel_index'))

    try:
        log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        log_date = date.today()

    total_cost = round(fuel_amount * fuel_price, 2)

    # Calculate Mileage based on previous odometer reading
    # Look for the immediate prior log by odometer reading
    prev_log = FuelLog.query.filter(
        FuelLog.vehicle_id == vehicle.id,
        FuelLog.odometer < odometer
    ).order_by(FuelLog.odometer.desc()).first()

    mileage = None
    if prev_log and fuel_amount > 0:
        distance_diff = odometer - prev_log.odometer
        if distance_diff > 0:
            mileage = round(distance_diff / fuel_amount, 2)

    new_log = FuelLog(
        vehicle_id=vehicle.id,
        date=log_date,
        odometer=odometer,
        fuel_amount=fuel_amount,
        fuel_price=fuel_price,
        total_cost=total_cost,
        mileage=mileage,
        is_full_tank=is_full_tank,
        notes=notes
    )
    db.session.add(new_log)

    # Update vehicle current odometer if higher
    if odometer > vehicle.current_odometer:
        vehicle.current_odometer = odometer

    db.session.commit()
    log_security_event('FUEL_LOG_ADD', f'Logged fuel purchase of ₹{total_cost} for {vehicle.license_plate}', user_id=user.id)
    flash('Fuel entry recorded successfully!', 'success')
    return redirect(url_for('fuel_index'))


@app.route('/fuel/delete/<int:log_id>', methods=['POST'])
@login_required
def delete_fuel_log(log_id):
    user = get_current_user()
    fuel_log = FuelLog.query.get_or_404(log_id)
    verify_vehicle_ownership(fuel_log.vehicle_id, user.id)

    db.session.delete(fuel_log)
    db.session.commit()
    log_security_event('FUEL_LOG_DELETE', f'Deleted fuel entry id {log_id}', user_id=user.id)
    flash('Fuel log removed.', 'info')
    return redirect(url_for('fuel_index'))


# ----------------------------------------------------
# SERVICE & MAINTENANCE ROUTES
# ----------------------------------------------------
@app.route('/service')
@login_required
def service_index():
    user = get_current_user()
    if not user.vehicles:
        flash('Please add a vehicle first.', 'warning')
        return redirect(url_for('vehicles'))

    vehicle = get_active_vehicle(user)
    records = ServiceRecord.query.filter_by(vehicle_id=vehicle.id).order_by(ServiceRecord.date.desc()).all()
    return render_template('service/index.html', vehicle=vehicle, records=records)


@app.route('/service/add', methods=['POST'])
@login_required
def add_service_record():
    user = get_current_user()
    vehicle = get_active_vehicle(user)
    if not vehicle:
        return redirect(url_for('vehicles'))

    date_str = request.form.get('date')
    odometer = request.form.get('odometer', type=float) or vehicle.current_odometer
    service_type = request.form.get('service_type', 'Routine Service').strip()
    service_center = request.form.get('service_center', '').strip()
    cost = request.form.get('cost', type=float) or 0.0
    invoice_no = request.form.get('invoice_no', '').strip()
    notes = request.form.get('notes', '').strip()

    if not date_str or not service_type:
        flash('Date and service type are required.', 'danger')
        return redirect(url_for('service_index'))

    try:
        service_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        service_date = date.today()

    record = ServiceRecord(
        vehicle_id=vehicle.id,
        date=service_date,
        odometer=odometer,
        service_type=service_type,
        service_center=service_center,
        cost=cost,
        invoice_no=invoice_no,
        notes=notes
    )
    db.session.add(record)

    if odometer > vehicle.current_odometer:
        vehicle.current_odometer = odometer

    db.session.commit()
    log_security_event('SERVICE_LOG_ADD', f'Added maintenance record: {service_type} (₹{cost})', user_id=user.id)
    flash('Service record saved successfully!', 'success')
    return redirect(url_for('service_index'))


@app.route('/service/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_service_record(record_id):
    user = get_current_user()
    record = ServiceRecord.query.get_or_404(record_id)
    verify_vehicle_ownership(record.vehicle_id, user.id)

    db.session.delete(record)
    db.session.commit()
    log_security_event('SERVICE_LOG_DELETE', f'Deleted service record id {record_id}', user_id=user.id)
    flash('Service record removed.', 'info')
    return redirect(url_for('service_index'))


# ----------------------------------------------------
# SMART REMINDERS ROUTES
# ----------------------------------------------------
@app.route('/reminders')
@login_required
def reminders_index():
    user = get_current_user()
    if not user.vehicles:
        return redirect(url_for('vehicles'))

    vehicle = get_active_vehicle(user)
    reminders = Reminder.query.filter_by(vehicle_id=vehicle.id).order_by(Reminder.is_completed.asc(), Reminder.due_date.asc()).all()
    
    # Pre-calculate status for display
    reminder_items = []
    for r in reminders:
        status = r.get_status(vehicle.current_odometer)
        reminder_items.append({
            'reminder': r,
            'status': status
        })

    return render_template('reminders/index.html', vehicle=vehicle, reminder_items=reminder_items)


@app.route('/reminders/add', methods=['POST'])
@login_required
def add_reminder():
    user = get_current_user()
    vehicle = get_active_vehicle(user)
    if not vehicle:
        return redirect(url_for('vehicles'))

    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Service').strip()
    due_date_str = request.form.get('due_date', '')
    due_odometer = request.form.get('due_odometer', type=float)
    notes = request.form.get('notes', '').strip()

    if not title:
        flash('Reminder title is required.', 'danger')
        return redirect(url_for('reminders_index'))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    reminder = Reminder(
        vehicle_id=vehicle.id,
        title=title,
        category=category,
        due_date=due_date,
        due_odometer=due_odometer,
        notes=notes
    )
    db.session.add(reminder)
    db.session.commit()

    log_security_event('REMINDER_ADD', f'Added reminder: {title}', user_id=user.id)
    flash(f'Reminder "{title}" set successfully.', 'success')
    return redirect(url_for('reminders_index'))


@app.route('/reminders/toggle/<int:reminder_id>', methods=['POST'])
@login_required
def toggle_reminder(reminder_id):
    user = get_current_user()
    reminder = Reminder.query.get_or_404(reminder_id)
    verify_vehicle_ownership(reminder.vehicle_id, user.id)

    reminder.is_completed = not reminder.is_completed
    db.session.commit()
    state = "completed" if reminder.is_completed else "active"
    flash(f'Reminder marked as {state}.', 'info')
    return redirect(url_for('reminders_index'))


@app.route('/reminders/delete/<int:reminder_id>', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    user = get_current_user()
    reminder = Reminder.query.get_or_404(reminder_id)
    verify_vehicle_ownership(reminder.vehicle_id, user.id)

    db.session.delete(reminder)
    db.session.commit()
    flash('Reminder removed.', 'info')
    return redirect(url_for('reminders_index'))


# ----------------------------------------------------
# EXPENSE ANALYTICS & API
# ----------------------------------------------------
@app.route('/expenses')
@login_required
def expenses_index():
    user = get_current_user()
    if not user.vehicles:
        return redirect(url_for('vehicles'))

    vehicle = get_active_vehicle(user)
    fuel_total = vehicle.total_fuel_spent
    service_total = vehicle.total_service_spent
    grand_total = fuel_total + service_total

    return render_template(
        'expenses/index.html',
        vehicle=vehicle,
        fuel_total=fuel_total,
        service_total=service_total,
        grand_total=grand_total
    )


@app.route('/api/analytics')
@login_required
def api_analytics():
    user = get_current_user()
    vehicle = get_active_vehicle(user)
    if not vehicle:
        return jsonify({'error': 'No active vehicle'}), 404

    # 1. Mileage Trend (Last 10 logs with calculated mileage, ordered chronologically)
    mileage_logs = [l for l in vehicle.fuel_logs if l.mileage and l.mileage > 0]
    mileage_logs.sort(key=lambda x: x.odometer)  # chronological
    mileage_data = {
        'labels': [l.date.strftime('%d %b') for l in mileage_logs[-10:]],
        'values': [l.mileage for l in mileage_logs[-10:]]
    }

    # 2. Monthly Expenses Breakdown (Last 6 months)
    monthly_labels = []
    fuel_monthly = []
    service_monthly = []

    today = date.today()
    for i in range(5, -1, -1):
        # Calculate month and year
        m = (today.month - i - 1) % 12 + 1
        y = today.year + ((today.month - i - 1) // 12)
        month_name = date(y, m, 1).strftime('%b %Y')
        monthly_labels.append(month_name)

        f_sum = sum(l.total_cost for l in vehicle.fuel_logs if l.date.year == y and l.date.month == m)
        s_sum = sum(s.cost for s in vehicle.service_records if s.date.year == y and s.date.month == m)
        fuel_monthly.append(round(f_sum, 2))
        service_monthly.append(round(s_sum, 2))

    # 3. Expense Distribution (Fuel vs Service Types)
    cat_distribution = {'Fuel': round(vehicle.total_fuel_spent, 2)}
    for s in vehicle.service_records:
        cat_distribution[s.service_type] = round(cat_distribution.get(s.service_type, 0.0) + s.cost, 2)

    return jsonify({
        'mileage': mileage_data,
        'monthly': {
            'labels': monthly_labels,
            'fuel': fuel_monthly,
            'service': service_monthly
        },
        'categories': {
            'labels': list(cat_distribution.keys()),
            'values': list(cat_distribution.values())
        }
    })


# ----------------------------------------------------
# CYBER SECURITY AUDIT HUB & VIVA REFERENCE
# ----------------------------------------------------
@app.route('/security/audit')
@login_required
def security_audit():
    user = get_current_user()
    # Fetch recent security logs for current user (or anonymous logs from this IP)
    logs = SecurityLog.query.filter_by(user_id=user.id).order_by(SecurityLog.timestamp.desc()).limit(30).all()

    # Viva Defense Q&A Data for examiners
    viva_qa = [
        {
            'topic': 'Password Storage & Cryptographic Hashing',
            'question': 'How does AutoVault securely store user passwords in the database?',
            'answer': 'AutoVault uses Werkzeug\'s generate_password_hash() which utilizes salted modern hashing (scrypt / PBKDF2 with SHA-256). Passwords are never stored in plaintext. Each password has a unique cryptographic salt preventing rainbow table attacks.'
        },
        {
            'topic': 'Broken Access Control & IDOR Prevention',
            'question': 'What is Insecure Direct Object Reference (IDOR) and how does AutoVault prevent it?',
            'answer': 'IDOR occurs when an application exposes a direct database ID in URLs or requests without validating ownership. In AutoVault, every vehicle, fuel log, service record, and reminder strictly queries by the authenticated user\'s ID from session (e.g. verify_vehicle_ownership). Unauthorized access attempts yield a 403 Forbidden.'
        },
        {
            'topic': 'SQL Injection (SQLi) Defense',
            'question': 'How is AutoVault protected against SQL Injection attacks?',
            'answer': 'AutoVault uses SQLAlchemy Object-Relational Mapping (ORM) which strictly executes parameterized SQL queries under the hood. User inputs are never concatenated into raw SQL strings, neutralizing SQL injection vectors.'
        },
        {
            'topic': 'Cross-Site Scripting (XSS) & CSRF Defense',
            'question': 'How does AutoVault prevent Cross-Site Scripting and Session Hijacking?',
            'answer': 'Jinja2 templating engine provides context-aware HTML auto-escaping by default, rendering malicious scripts inert. Session cookies are configured with HttpOnly=True (preventing JavaScript from accessing the session cookie) and SameSite=Lax (mitigating Cross-Site Request Forgery).'
        },
        {
            'topic': 'Security Audit Trails & Incident Response',
            'question': 'Why is the Security Audit Log crucial for cyber defense?',
            'answer': 'The security audit log captures all authentication attempts (including failed password brute-force events), IP addresses, user agents, and sensitive record mutations. This provides full traceability, non-repudiation, and assists in post-incident forensics.'
        }
    ]

    return render_template('security/audit.html', logs=logs, viva_qa=viva_qa)


# ----------------------------------------------------
# DATA EXPORT
# ----------------------------------------------------
@app.route('/export/fuel/csv')
@login_required
def export_fuel_csv():
    user = get_current_user()
    vehicle = get_active_vehicle(user)
    if not vehicle:
        return redirect(url_for('vehicles'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Odometer (km)', 'Fuel Amount (L)', 'Price per Unit (INR)', 'Total Cost (INR)', 'Mileage (km/L)', 'Full Tank', 'Notes'])

    for log in vehicle.fuel_logs:
        writer.writerow([
            log.date.strftime('%Y-%m-%d'),
            log.odometer,
            log.fuel_amount,
            log.fuel_price,
            log.total_cost,
            log.mileage if log.mileage else 'N/A',
            'Yes' if log.is_full_tank else 'No',
            log.notes or ''
        ])

    output.seek(0)
    filename = f"autovault_fuel_{vehicle.license_plate}_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


# ----------------------------------------------------
# DATABASE INITIALIZATION HELPER
# ----------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
