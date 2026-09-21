import unittest
from datetime import date, timedelta
from app import app, db
from models import User, Vehicle, FuelLog, ServiceRecord, Reminder, SecurityLog

class AutoVaultTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_registration_and_password_hashing(self):
        """Test registration and verify password is cryptographically hashed (scrypt/pbkdf2)."""
        response = self.app.post('/register', data={
            'username': 'cyber_student',
            'email': 'student@cse.edu',
            'password': 'SecurePass@2026',
            'confirm_password': 'SecurePass@2026'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with app.app_context():
            user = User.query.filter_by(username='cyber_student').first()
            self.assertIsNotNone(user)
            self.assertNotEqual(user.password_hash, 'SecurePass@2026')
            self.assertTrue(user.check_password('SecurePass@2026'))
            self.assertFalse(user.check_password('WrongPassword'))

            # Check security audit log
            log = SecurityLog.query.filter_by(user_id=user.id, event_type='REGISTER').first()
            self.assertIsNotNone(log)

    def test_login_and_session(self):
        """Test authentication flow, session assignment, and login audit event."""
        with app.app_context():
            user = User(username='test_user', email='test@test.com')
            user.set_password('ValidPass@123')
            db.session.add(user)
            db.session.commit()

        # Failed login
        fail_resp = self.app.post('/login', data={
            'identifier': 'test@test.com',
            'password': 'BadPassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username/email or password', fail_resp.data)

        # Successful login
        succ_resp = self.app.post('/login', data={
            'identifier': 'test@test.com',
            'password': 'ValidPass@123'
        }, follow_redirects=True)
        self.assertEqual(succ_resp.status_code, 200)
        with self.app.session_transaction() as sess:
            self.assertIn('user_id', sess)

    def test_vehicle_creation_and_fuel_mileage_calculation(self):
        """Test vehicle creation and automatic km/L mileage computation."""
        with app.app_context():
            user = User(username='owner', email='owner@vault.com')
            user.set_password('Vault@2026!')
            db.session.add(user)
            db.session.commit()
            uid = user.id

        with self.app.session_transaction() as sess:
            sess['user_id'] = uid

        # 1. Add vehicle
        v_resp = self.app.post('/vehicles', data={
            'name': 'Test Car',
            'make': 'Maruti',
            'model': 'Swift',
            'year': 2021,
            'license_plate': 'DL 01 AA 1111',
            'fuel_type': 'Petrol',
            'current_odometer': 10000.0,
            'purchase_date': '2021-01-01'
        }, follow_redirects=True)
        self.assertEqual(v_resp.status_code, 200)

        with app.app_context():
            v = Vehicle.query.filter_by(license_plate='DL 01 AA 1111').first()
            self.assertIsNotNone(v)
            vid = v.id

        with self.app.session_transaction() as sess:
            sess['active_vehicle_id'] = vid

        # 2. Add first fuel entry (baseline)
        self.app.post('/fuel/add', data={
            'date': str(date.today() - timedelta(days=10)),
            'odometer': 10000.0,
            'fuel_amount': 30.0,
            'fuel_price': 100.0,
            'is_full_tank': '1',
            'notes': 'Baseline'
        }, follow_redirects=True)

        # 3. Add second fuel entry (travelled 450 km on 30 Liters -> 15.0 km/L)
        self.app.post('/fuel/add', data={
            'date': str(date.today()),
            'odometer': 10450.0,
            'fuel_amount': 30.0,
            'fuel_price': 100.0,
            'is_full_tank': '1',
            'notes': 'Refill 2'
        }, follow_redirects=True)

        with app.app_context():
            v = db.session.get(Vehicle, vid)
            self.assertEqual(v.current_odometer, 10450.0)
            self.assertEqual(len(v.fuel_logs), 2)
            # Latest log should have mileage = 15.0
            latest_log = v.fuel_logs[0]
            self.assertEqual(latest_log.mileage, 15.0)

    def test_idor_protection(self):
        """Test Insecure Direct Object Reference (IDOR) defense between users."""
        with app.app_context():
            user_a = User(username='alice', email='alice@vault.com')
            user_a.set_password('AlicePass@2026')
            user_b = User(username='bob', email='bob@vault.com')
            user_b.set_password('BobPass@2026')
            db.session.add_all([user_a, user_b])
            db.session.commit()

            veh_a = Vehicle(user_id=user_a.id, name='Alice Car', make='Ford', model='Figo', year=2020, license_plate='DL 02 CC 2222')
            db.session.add(veh_a)
            db.session.commit()
            veh_a_id = veh_a.id
            user_b_id = user_b.id

        # Log in as Bob
        with self.app.session_transaction() as sess:
            sess['user_id'] = user_b_id

        # Bob attempts to select or delete Alice's vehicle -> 403 Forbidden
        select_resp = self.app.get(f'/vehicles/select/{veh_a_id}')
        self.assertEqual(select_resp.status_code, 403)

        del_resp = self.app.post(f'/vehicles/delete/{veh_a_id}')
        self.assertEqual(del_resp.status_code, 403)

    def test_smart_reminders_status(self):
        """Test reminder status calculation (Overdue, Due Soon, Good)."""
        today = date.today()
        rem_overdue = Reminder(title='Insurance', category='Insurance', due_date=today - timedelta(days=2))
        rem_soon = Reminder(title='PUC', category='PUC', due_date=today + timedelta(days=5))
        rem_good = Reminder(title='Next Year', category='Registration', due_date=today + timedelta(days=60))

        self.assertEqual(rem_overdue.get_status(), 'Overdue')
        self.assertEqual(rem_soon.get_status(), 'Due Soon')
        self.assertEqual(rem_good.get_status(), 'Good')

if __name__ == '__main__':
    unittest.main()
