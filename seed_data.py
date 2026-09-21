"""
AutoVault Seed Data Script
Populates the database with realistic sample vehicles, fuel logs, service history,
smart reminders, and cyber security audit trails for academic demonstrations and viva defense.
"""

from datetime import date, timedelta, datetime, timezone
from app import app, db
from models import User, Vehicle, FuelLog, ServiceRecord, Reminder, SecurityLog

def seed_database():
    with app.app_context():
        # Clean and create all tables
        db.create_all()

        # Check if demo user already exists
        demo_user = User.query.filter_by(email='demo@autovault.com').first()
        if demo_user:
            print("Demo user already exists. Cleaning up previous demo data...")
            db.session.delete(demo_user)
            db.session.commit()

        print("Creating demo user (demo@autovault.com / AutoVault@2026)...")
        user = User(
            username='arjun_sharma',
            email='demo@autovault.com'
        )
        user.set_password('AutoVault@2026')
        db.session.add(user)
        db.session.commit()

        # Log account creation audit event
        reg_log = SecurityLog(
            user_id=user.id,
            event_type='REGISTER',
            ip_address='192.168.1.45',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
            details=f'Demo account registered: {user.username}',
            timestamp=datetime.now(timezone.utc) - timedelta(days=90)
        )
        login_log = SecurityLog(
            user_id=user.id,
            event_type='LOGIN_SUCCESS',
            ip_address='192.168.1.45',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0',
            details='Initial successful login with scrypt authentication',
            timestamp=datetime.now(timezone.utc) - timedelta(days=90)
        )
        failed_sim_log = SecurityLog(
            user_id=user.id,
            event_type='LOGIN_FAILED',
            ip_address='203.0.113.19',
            user_agent='Python-requests/2.31.0 (Automated Probe)',
            details='Failed login attempt with invalid credentials (Simulated Brute-force Blocked)',
            timestamp=datetime.now(timezone.utc) - timedelta(days=15)
        )
        db.session.add_all([reg_log, login_log, failed_sim_log])

        # ---------------------------------------------
        # VEHICLE 1: Honda City V (Sedan)
        # ---------------------------------------------
        print("Adding Vehicle 1: Honda City V...")
        car = Vehicle(
            user_id=user.id,
            name='Daily City Sedan',
            make='Honda',
            model='City V',
            year=2022,
            license_plate='DL 03 CA 9021',
            fuel_type='Petrol',
            current_odometer=24820.0,
            purchase_date=date.today() - timedelta(days=730)
        )
        db.session.add(car)
        db.session.commit()

        # Fuel logs for Honda City (chronological odometer readings)
        car_fuel_entries = [
            # date_offset, odo, liters, price
            (75, 23100.0, 38.0, 96.72, None),        # Baseline log
            (60, 23640.0, 36.5, 96.72, 14.79),       # (540 km / 36.5 L) = 14.79 km/L
            (45, 24180.0, 35.0, 97.15, 15.43),       # (540 km / 35.0 L) = 15.43 km/L
            (30, 24690.0, 34.2, 97.40, 14.91),       # (510 km / 34.2 L) = 14.91 km/L
            (15, 25210.0, 34.5, 97.40, 15.07),       # (520 km / 34.5 L) = 15.07 km/L
            (2,  25720.0, 36.0, 98.20, 14.17),       # (510 km / 36.0 L) = 14.17 km/L
        ]

        for days_ago, odo, liters, price, mileage in car_fuel_entries:
            cost = round(liters * price, 2)
            log = FuelLog(
                vehicle_id=car.id,
                date=date.today() - timedelta(days=days_ago),
                odometer=odo,
                fuel_amount=liters,
                fuel_price=price,
                total_cost=cost,
                mileage=mileage,
                is_full_tank=True,
                notes="HPCL AutoPort Fuel Station"
            )
            db.session.add(log)

        car.current_odometer = 25720.0

        # Service records for Honda City
        car_services = [
            (180, 20000.0, "Periodic Maintenance", "Apex Honda Authorized Workshop", 4850.0, "INV-HON-7812", "General checkup, synthetic engine oil 0W-20, oil filter, air filter cleaning"),
            (90, 22500.0, "Tire Rotation & Balancing", "Speedway Wheel Care", 1200.0, "INV-TYR-3401", "4-wheel balancing and rotation, nitrogen top-up"),
            (25, 25000.0, "AC & Cabin Filter", "Apex Honda Authorized Workshop", 2150.0, "INV-HON-9102", "AC evaporator cleaning, replaced anti-bacterial cabin filter")
        ]

        for days_ago, odo, stype, center, cost, inv, notes in car_services:
            sr = ServiceRecord(
                vehicle_id=car.id,
                date=date.today() - timedelta(days=days_ago),
                odometer=odo,
                service_type=stype,
                service_center=center,
                cost=cost,
                invoice_no=inv,
                notes=notes
            )
            db.session.add(sr)

        # Smart Reminders for Honda City
        car_reminders = [
            ("Comprehensive Motor Insurance Renewal", "Insurance Renewal", date.today() + timedelta(days=12), None, "Policy #HD-7821-CAR with HDFC ERGO (Expiring soon)"),
            ("PUC / Pollution Under Control Test", "PUC / Emission Test", date.today() + timedelta(days=5), None, "Valid at any authorized petrol bunk emission station"),
            ("30,000 km Major Service Milestone", "Scheduled Maintenance", None, 30000.0, "Transmission fluid check, spark plugs inspection, brake pads wear inspection")
        ]

        for title, cat, due_d, due_o, notes in car_reminders:
            rem = Reminder(
                vehicle_id=car.id,
                title=title,
                category=cat,
                due_date=due_d,
                due_odometer=due_o,
                notes=notes
            )
            db.session.add(rem)

        # ---------------------------------------------
        # VEHICLE 2: Royal Enfield Hunter 350 (Motorcycle)
        # ---------------------------------------------
        print("Adding Vehicle 2: Royal Enfield Hunter 350...")
        bike = Vehicle(
            user_id=user.id,
            name='Weekend Cruiser',
            make='Royal Enfield',
            model='Hunter 350',
            year=2023,
            license_plate='DL 08 XY 4512',
            fuel_type='Petrol',
            current_odometer=6840.0,
            purchase_date=date.today() - timedelta(days=365)
        )
        db.session.add(bike)
        db.session.commit()

        bike_fuel_entries = [
            (40, 6100.0, 11.0, 96.72, None),       # Baseline
            (28, 6480.0, 10.5, 96.72, 36.19),      # (380 km / 10.5 L) = 36.19 km/L
            (14, 6840.0, 10.0, 97.40, 36.00),      # (360 km / 10.0 L) = 36.00 km/L
            (1,  7210.0, 10.2, 98.20, 36.27)       # (370 km / 10.2 L) = 36.27 km/L
        ]

        for days_ago, odo, liters, price, mileage in bike_fuel_entries:
            cost = round(liters * price, 2)
            log = FuelLog(
                vehicle_id=bike.id,
                date=date.today() - timedelta(days=days_ago),
                odometer=odo,
                fuel_amount=liters,
                fuel_price=price,
                total_cost=cost,
                mileage=mileage,
                is_full_tank=True,
                notes="IOCL Station"
            )
            db.session.add(log)

        bike.current_odometer = 7210.0

        # Service for Bike
        bike_sr = ServiceRecord(
            vehicle_id=bike.id,
            date=date.today() - timedelta(days=60),
            odometer=5000.0,
            service_type="Periodic Maintenance",
            service_center="Royal Enfield Service Hub",
            cost=2450.0,
            invoice_no="INV-RE-2209",
            notes="5,000 km scheduled service: Engine oil change (Liquid Gun 15W-50), chain cleaning & lubing"
        )
        db.session.add(bike_sr)

        # Reminder for Bike
        bike_rem = Reminder(
            vehicle_id=bike.id,
            title="Chain Cleaning & Lubrication",
            category="Scheduled Maintenance",
            due_date=date.today() + timedelta(days=18),
            due_odometer=7500.0,
            notes="Clean with Motul chain cleaner and apply chain lube"
        )
        db.session.add(bike_rem)

        db.session.commit()
        print("Seed data successfully inserted!")
        print("--------------------------------------------------")
        print("Demo Account Credentials:")
        print("Email:    demo@autovault.com")
        print("Password: AutoVault@2026")
        print("--------------------------------------------------")

if __name__ == '__main__':
    seed_database()
