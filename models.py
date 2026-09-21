from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    vehicles = db.relationship('Vehicle', backref='owner', cascade='all, delete-orphan', lazy=True)
    security_logs = db.relationship('SecurityLog', backref='user', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password):
        """Securely hash password using Werkzeug's modern scrypt/pbkdf2 algorithm."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against stored cryptographic hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "Daily Commute", "Highway Beast"
    make = db.Column(db.String(50), nullable=False)  # e.g., Honda, Toyota, Hyundai
    model = db.Column(db.String(50), nullable=False)  # e.g., City, Fortuner, Creta
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(30), nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False, default='Petrol')  # Petrol, Diesel, Electric, Hybrid, CNG
    current_odometer = db.Column(db.Float, nullable=False, default=0.0)
    purchase_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    fuel_logs = db.relationship('FuelLog', backref='vehicle', cascade='all, delete-orphan', lazy=True, order_by='desc(FuelLog.odometer)')
    service_records = db.relationship('ServiceRecord', backref='vehicle', cascade='all, delete-orphan', lazy=True, order_by='desc(ServiceRecord.date)')
    reminders = db.relationship('Reminder', backref='vehicle', cascade='all, delete-orphan', lazy=True, order_by='Reminder.due_date')

    @property
    def total_fuel_spent(self):
        return sum(log.total_cost for log in self.fuel_logs)

    @property
    def total_service_spent(self):
        return sum(rec.cost for rec in self.service_records)

    @property
    def total_expenses(self):
        return self.total_fuel_spent + self.total_service_spent

    @property
    def average_mileage(self):
        valid_logs = [log.mileage for log in self.fuel_logs if log.mileage and log.mileage > 0]
        if not valid_logs:
            return 0.0
        return round(sum(valid_logs) / len(valid_logs), 2)

    def __repr__(self):
        return f'<Vehicle {self.make} {self.model} ({self.license_plate})>'


class FuelLog(db.Model):
    __tablename__ = 'fuel_logs'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    odometer = db.Column(db.Float, nullable=False)
    fuel_amount = db.Column(db.Float, nullable=False)  # Liters or kWh
    fuel_price = db.Column(db.Float, nullable=False)  # Price per unit (e.g. ₹/L)
    total_cost = db.Column(db.Float, nullable=False)
    mileage = db.Column(db.Float, nullable=True)  # km/L or km/kWh computed from previous log
    is_full_tank = db.Column(db.Boolean, default=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<FuelLog {self.date} - Odo {self.odometer}>'


class ServiceRecord(db.Model):
    __tablename__ = 'service_records'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    odometer = db.Column(db.Float, nullable=False)
    service_type = db.Column(db.String(80), nullable=False)  # Routine Maintenance, Oil Change, Brakes, Tires, Battery, Repairs
    service_center = db.Column(db.String(120), nullable=True)
    cost = db.Column(db.Float, nullable=False, default=0.0)
    invoice_no = db.Column(db.String(60), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f'<ServiceRecord {self.service_type} on {self.date}>'


class Reminder(db.Model):
    __tablename__ = 'reminders'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)  # e.g., "Insurance Policy Renewal"
    category = db.Column(db.String(60), nullable=False)  # Insurance, PUC / Emission, Registration, Service, Tire Rotation
    due_date = db.Column(db.Date, nullable=True)
    due_odometer = db.Column(db.Float, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def get_status(self, current_odo=None):
        """
        Dynamically calculate reminder status:
        - 'Completed'
        - 'Overdue' (past due date or odometer exceeded)
        - 'Due Soon' (within 15 days or within 500 km)
        - 'Good'
        """
        if self.is_completed:
            return 'Completed'

        today = date.today()
        is_overdue = False
        is_due_soon = False

        if self.due_date:
            days_left = (self.due_date - today).days
            if days_left < 0:
                is_overdue = True
            elif days_left <= 15:
                is_due_soon = True

        if current_odo is not None and self.due_odometer:
            km_left = self.due_odometer - current_odo
            if km_left < 0:
                is_overdue = True
            elif km_left <= 500:
                is_due_soon = True

        if is_overdue:
            return 'Overdue'
        if is_due_soon:
            return 'Due Soon'
        return 'Good'

    def __repr__(self):
        return f'<Reminder {self.title}>'


class SecurityLog(db.Model):
    __tablename__ = 'security_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False)  # LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, REGISTER, etc.
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)

    def __repr__(self):
        return f'<SecurityLog {self.event_type} at {self.timestamp}>'
