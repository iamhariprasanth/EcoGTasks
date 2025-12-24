# EcoGTasks - Flask Task Management System

A comprehensive **Jira-like** task management web application built with Flask and SQLite, designed for teams of ~100 employees.

## 🚀 Features

### User Management
- **Role-based access control** (Admin, Manager, Employee)
- Secure login/logout with session management
- Admin-only user registration
- Password hashing with Werkzeug

### Task Management
- Full CRUD operations for tasks
- Task fields: Title, Description, Status, Priority, Assignee, Due Date
- Task comments and discussions
- Complete audit history/activity log
- Quick status updates and reassignment
- Advanced filtering (status, priority, assignee, project)
- Pagination and search

### Project Management
- Create and manage projects
- Team member assignment
- Project-based task organization
- Progress tracking

### Dashboards
- **Admin**: System-wide stats, user management, recent activity
- **Manager**: Team workload, project overview
- **Employee**: Personal tasks, deadlines, priorities

### Security
- CSRF protection on all forms
- Secure session cookies
- Input validation with WTForms
- Role-based route protection
- SQL injection prevention via SQLAlchemy ORM

## 📁 Project Structure

```
EcoGTasks/
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── seed.py               # Demo data seeder
├── app/
│   ├── __init__.py       # App factory
│   ├── config.py         # Configuration
│   ├── models.py         # Database models
│   ├── routes/
│   │   ├── auth.py       # Authentication
│   │   ├── dashboard.py  # Dashboards
│   │   ├── tasks.py      # Task CRUD
│   │   ├── projects.py   # Project management
│   │   └── admin.py      # Admin panel
│   ├── templates/        # Jinja2 templates
│   ├── static/css/       # Stylesheets
│   └── utils/
│       ├── decorators.py # Access control
│       └── forms.py      # WTForms
└── instance/
    └── taskmanager.db    # SQLite database
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip

### Setup Steps

1. **Navigate to project directory**
   ```bash
   cd /Users/hariprasanthmadhavan/EcoGTasks
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or: venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database and seed demo data**
   ```bash
   python seed.py
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

## 👤 Demo Credentials

| Role     | Email                  | Password    |
|----------|------------------------|-------------|
| Admin    | admin@company.com      | admin123    |
| Manager  | manager@company.com    | manager123  |
| Manager  | sarah@company.com      | sarah123    |
| Employee | employee@company.com   | employee123 |
| Employee | john@company.com       | john123     |
| Employee | alice@company.com      | alice123    |
| Employee | bob@company.com        | bob123      |

## 🔐 Security Best Practices

1. **Password Hashing**: Uses Werkzeug's `generate_password_hash` with PBKDF2
2. **CSRF Protection**: Flask-WTF CSRFProtect on all forms
3. **Session Security**: HTTPOnly cookies, secure flag for HTTPS
4. **Input Validation**: Server-side validation with WTForms
5. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
6. **Access Control**: Custom decorators (`@admin_required`, `@manager_required`)

## ⚙️ Configuration

Edit `app/config.py` to customize:

```python
# Change secret key for production
SECRET_KEY = 'your-secure-production-key'

# Session timeout (default: 8 hours)
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

# Pagination settings
TASKS_PER_PAGE = 10
```

## 🏗️ Production Deployment

For production use:

1. Set environment variables:
   ```bash
   export FLASK_CONFIG=production
   export SECRET_KEY='your-very-secure-random-key'
   ```

2. Use a production WSGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

3. Enable HTTPS and set `SESSION_COOKIE_SECURE = True`

## 📊 Database

The application uses SQLite with SQLAlchemy ORM. Database file is created at `instance/taskmanager.db`.

### Models
- **User**: Authentication and role management
- **Project**: Task organization
- **Task**: Core task entity with status workflow
- **Comment**: Task discussions
- **TaskHistory**: Audit trail

## 📝 License

MIT License - Feel free to use and modify.
