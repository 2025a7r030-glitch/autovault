import re
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from models import db, User, Vehicle, SecurityLog

def login_required(f):
    """
    Decorator to protect routes from unauthenticated access.
    Redirects to login page if session does not contain user_id.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Retrieve the currently logged-in User instance or None."""
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None


def get_active_vehicle(user):
    """
    Get the currently active vehicle for the user.
    Uses session['active_vehicle_id'] if valid, otherwise defaults to the first vehicle.
    """
    if not user or not user.vehicles:
        return None

    active_id = session.get('active_vehicle_id')
    if active_id:
        vehicle = Vehicle.query.filter_by(id=active_id, user_id=user.id).first()
        if vehicle:
            return vehicle

    # Default to first vehicle
    vehicle = user.vehicles[0]
    session['active_vehicle_id'] = vehicle.id
    return vehicle


def verify_vehicle_ownership(vehicle_id, user_id):
    """
    IDOR (Insecure Direct Object Reference) Prevention Helper:
    Ensures that the vehicle belongs strictly to the authenticated user.
    """
    vehicle = Vehicle.query.filter_by(id=vehicle_id, user_id=user_id).first()
    if not vehicle:
        abort(403)  # Forbidden access
    return vehicle


def log_security_event(event_type, details=None, user_id=None):
    """
    Security Audit Trail:
    Logs every security-sensitive operation (Logins, Failed attempts, Data deletions, Vehicle additions).
    """
    try:
        # Determine client IP address
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.remote_addr or '127.0.0.1'

        user_agent = request.user_agent.string if request.user_agent else 'Unknown'
        uid = user_id or session.get('user_id')

        log = SecurityLog(
            user_id=uid,
            event_type=event_type,
            ip_address=ip[:45],
            user_agent=user_agent[:255],
            details=(details or '')[:255]
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Warning: Failed to write security log: {e}")


def validate_password_strength(password):
    """
    Validates password strength:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special symbol
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one numeric digit (0-9)."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    return True, "Strong password."
