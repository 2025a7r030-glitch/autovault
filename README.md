# AutoVault — Secure and Personalized Vehicle Management System

**Academic Project**: 3rd-Semester B.Tech Computer Science & Engineering (Specialization: Cyber Security)  
**Tech Stack**: Python 3.13, Flask 3.1, SQLite, SQLAlchemy ORM, HTML5/CSS3, JavaScript, Chart.js, Lucide Icons.

---

## 1. Project Overview

**AutoVault** is an all-in-one vehicle management platform designed to centralize and secure vehicle documentation, service bills, fuel receipts, scheduled maintenance, and compliance reminders into a unified digital vault.

### Core Modules:
1. **Multi-Vehicle Garage**: Store specifications, purchase dates, and current odometer for multiple vehicles (cars, motorcycles, scooters, SUVs) with active vehicle switching.
2. **Fuel Tracking & Consumption Analytics**: Record fuel purchases with automatic **km/L (or km/kWh)** mileage calculation, cost per liter, and smart warnings for abnormal consumption or monthly budget overshoot.
3. **Digital Service & Maintenance Log**: Maintain an auditable digital service book capturing workshops, invoice numbers, service categories, parts replaced, and costs.
4. **Smart Reminders & Compliance**: Automatic deadline and odometer triggers for Insurance renewal, Pollution Under Control (PUC) certificate, and periodic service milestones (with *Good*, *Due Soon*, and *Overdue* badges).
5. **Expense Analytics & Reports**: Cost-per-km metrics, monthly breakdown charts, category distribution doughnut charts, and CSV data export.
6. **Cyber Security Operations Center & Viva Hub**: Dedicated security dashboard featuring a live security audit trail, OWASP Top 10 defense analysis, and viva defense answers for academic evaluation.

---

## 2. Cyber Security Architecture & Viva Defense Guide

Because AutoVault is designed for a **Cyber Security** specialization, security controls are built into every layer:

| Security Domain | Implementation in AutoVault | Viva Defense Explanation |
| :--- | :--- | :--- |
| **Password Security** | `werkzeug.security.generate_password_hash` | Uses `scrypt` / `pbkdf2:sha256` with unique cryptographic salts. Plaintext passwords are never stored. Resists rainbow table & dictionary attacks. |
| **Access Control (IDOR Defense)** | Scoped queries & `verify_vehicle_ownership()` | Prevents Insecure Direct Object References (OWASP A01). Users can only view or mutate assets tied to their authenticated session (`session['user_id']`). |
| **SQL Injection Defense** | SQLAlchemy ORM Parameterization | All SQL queries are strictly compiled as parameterized statements. User input is never concatenated into raw SQL strings. |
| **XSS Defense** | Jinja2 Context-Aware Escaping | Eliminates Cross-Site Scripting by automatically escaping dynamic user input before rendering in the DOM. |
| **Session Security** | Hardened Cookie Flags | `SESSION_COOKIE_HTTPONLY = True` prevents client-side JS theft; `SESSION_COOKIE_SAMESITE = 'Lax'` prevents CSRF exploitation. |
| **Security Audit Logging** | `SecurityLog` Table & Forensics | Real-time logging of login events, failed attempts, and data deletions with client IP and User-Agent fingerprinting. |

---

## 3. Project Structure

```
vehicle-tracker/
│
├── app.py                     # Main Flask application, routes, session hardening & export endpoints
├── models.py                  # SQLAlchemy ORM models (User, Vehicle, FuelLog, ServiceRecord, Reminder, SecurityLog)
├── security.py                # Security decorators, password complexity check, IDOR verification, audit logger
├── seed_data.py               # Pre-populated realistic demo dataset for instant viva demonstration
├── test_app.py                # Automated unit test suite verifying auth, IDOR defense, and calculations
├── requirements.txt           # Python dependencies (Flask, Flask-SQLAlchemy, Werkzeug)
│
├── static/
│   ├── css/
│   │   └── style.css          # Responsive dark/glassmorphic UI theme (desktop, tablet, mobile)
│   └── js/
│       └── main.js            # Sidebar toggle, vehicle switcher, alert auto-dismiss, Lucide icons
│
└── templates/
    ├── base.html              # Core navigation layout, vehicle switcher, flash alerts
    ├── auth/
    │   ├── login.html         # Login with security badges and 1-click Viva Demo Fill
    │   └── register.html      # Registration with real-time password strength meter
    ├── dashboard.html         # Central vehicle dashboard with stat cards, warning alerts, and Chart.js
    ├── vehicles/
    │   └── index.html         # Garage management (add, edit, switch active vehicle)
    ├── fuel/
    │   └── index.html         # Fuel logging, mileage calculator & consumption history
    ├── service/
    │   └── index.html         # Maintenance timeline & service records
    ├── reminders/
    │   └── index.html         # Smart due-date and odometer-based reminders
    ├── expenses/
    │   └── index.html         # Lifetime cost breakdown & financial analytics
    └── security/
        └── audit.html         # Live Cyber Security audit log & Examiner Viva Q&A Guide
```

---

## 4. Setup & Execution Instructions

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Seed Realistic Demo Data (Recommended for Viva)
Run the automated seed script to create tables and populate a demo account with 2 vehicles (Honda City Sedan & Royal Enfield Bike), realistic fuel logs, service history, reminders, and audit records:
```bash
python seed_data.py
```

### Step 3: Start the Flask Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Step 4: Sign In with Demo Credentials
- **Email**: `demo@autovault.com`
- **Password**: `AutoVault@2026`
*(You can also simply click the **"Load Demo Credentials"** button directly on the login page for 1-click viva presentation).*

---

## 5. Running Automated Tests

Run the test suite to demonstrate automated software testing and security test cases:
```bash
python test_app.py
```
All 5 test cases will execute:
- User Registration & Password Hashing
- Login Flow & Session Generation
- Vehicle Creation & Automatic km/L Mileage Calculation
- IDOR Access Control Defense (Cross-user asset isolation)
- Smart Reminder Status Calculation

---

## 6. Academic Viva Defense Cheat Sheet

### Q1: How does AutoVault ensure passwords are secure?
**Answer**: AutoVault uses Werkzeug's `generate_password_hash()`. It computes a salted cryptographic hash using `scrypt` or `PBKDF2-HMAC-SHA256`. Each user receives a unique cryptographic salt, rendering pre-computed rainbow table attacks impossible. When checking passwords, `check_password_hash()` compares the hash in constant time to defend against timing attacks.

### Q2: What is an IDOR vulnerability and how did you prevent it?
**Answer**: Insecure Direct Object Reference (OWASP A01: Broken Access Control) occurs when an attacker modifies a parameter (e.g. `vehicle_id=5`) to access another user's private data. In AutoVault, all database queries in CRUD routes enforce ownership checks via `verify_vehicle_ownership(vehicle_id, current_user.id)` and `session['user_id']`. If an unauthorized access is detected, a `403 Forbidden` response is returned.

### Q3: How is SQL Injection prevented?
**Answer**: AutoVault uses SQLAlchemy ORM. Instead of constructing raw SQL queries with string formatting, SQLAlchemy sends SQL queries with placeholders and binds user inputs as parameters. The SQLite database engine compiles the query structure first, ensuring user input can never alter query logic.

### Q4: How is fuel mileage computed?
**Answer**: Whenever a fuel log is submitted with an odometer reading, the system finds the immediate prior fuel log for that specific vehicle (`odometer < current_odometer`). It calculates:
$$\text{Mileage (km/L)} = \frac{\text{Current Odometer} - \text{Previous Odometer}}{\text{Fuel Volume in Liters}}$$
If consumption drops significantly below the vehicle's standard threshold, an automated high consumption warning banner is raised on the dashboard.
