"""
SQLAlchemy Database Models
Defines User, Project, Task, Comment, and TaskHistory models with relationships.
"""
from datetime import datetime, timezone, timedelta
from enum import Enum
from time import time
import jwt

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager

# IST Timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    """Get current datetime in IST timezone."""
    return datetime.now(IST)


def get_ist_date():
    """Get current date in IST timezone."""
    return datetime.now(IST).date()


# Enums for task management
class UserRole(Enum):
    """User roles for access control."""
    ADMIN = 'admin'
    MANAGER = 'manager'
    EMPLOYEE = 'employee'


class TaskStatus(Enum):
    """Task status options."""
    TODO = 'To Do'
    IN_PROGRESS = 'In Progress'
    BLOCKED = 'Blocked'
    DONE = 'Done'


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 'Low'
    MEDIUM = 'Medium'
    HIGH = 'High'


# Association table for project members (many-to-many)
project_members = db.Table(
    'project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=get_ist_now)
)


class User(UserMixin, db.Model):
    """
    User model with authentication and role-based access.
    
    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        password_hash: Hashed password (never store plain text!)
        role: User role (admin, manager, employee)
        is_active: Account status
        is_approved: Whether admin has approved the account
        created_at: Account creation timestamp
        last_login: Last login timestamp
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.EMPLOYEE.value)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # New field for admin approval
    created_at = db.Column(db.DateTime, default=get_ist_now)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assigned_to',
                                      backref='assignee', lazy='dynamic')
    created_tasks = db.relationship('Task', foreign_keys='Task.created_by',
                                     backref='creator', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    projects = db.relationship('Project', secondary=project_members,
                               backref=db.backref('members', lazy='dynamic'))
    created_projects = db.relationship('Project', foreign_keys='Project.created_by',
                                        backref='owner', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN.value
    
    def is_manager(self):
        """Check if user has manager role."""
        return self.role == UserRole.MANAGER.value
    
    def is_manager_or_admin(self):
        """Check if user has manager or admin role."""
        return self.role in [UserRole.ADMIN.value, UserRole.MANAGER.value]
    
    def can_access_project(self, project):
        """Check if user can access a project."""
        if self.is_admin():
            return True
        return project in self.projects or project.created_by == self.id
    
    def get_reset_password_token(self, expires_in=3600):
        """Generate a password reset token."""
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_reset_password_token(token):
        """Verify the password reset token and return the user."""
        try:
            id = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )['reset_password']
        except:
            return None
        return User.query.get(id)
    
    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


class Project(db.Model):
    """
    Project model for organizing tasks.
    
    Attributes:
        id: Primary key
        name: Project name
        description: Project description
        created_by: User who created the project
        created_at: Creation timestamp
        is_active: Project status
    """
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_now)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy='dynamic',
                           cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'


class Task(db.Model):
    """
    Task model with Jira-like features.
    
    Attributes:
        id: Primary key
        title: Task title
        description: Detailed description
        status: Current status (To Do, In Progress, Done)
        priority: Priority level (Low, Medium, High)
        assigned_to: User assigned to the task
        created_by: User who created the task
        project_id: Parent project
        due_date: Task deadline
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default=TaskStatus.TODO.value, index=True)
    priority = db.Column(db.String(20), nullable=False, default=TaskPriority.MEDIUM.value, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False, index=True)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=get_ist_now)
    updated_at = db.Column(db.DateTime, default=get_ist_now, onupdate=get_ist_now)
    
    # Time tracking fields
    estimated_hours = db.Column(db.Float, default=0)  # Original estimate in hours
    completion_percentage = db.Column(db.Integer, default=0)  # 0-100%
    
    # Relationships
    comments = db.relationship('Comment', backref='task', lazy='dynamic',
                              cascade='all, delete-orphan')
    history = db.relationship('TaskHistory', backref='task', lazy='dynamic',
                             cascade='all, delete-orphan')
    time_logs = db.relationship('TimeLog', backref='task', lazy='dynamic',
                               cascade='all, delete-orphan')
    
    @property
    def logged_hours(self):
        """Calculate total logged hours from time logs."""
        total = db.session.query(db.func.sum(TimeLog.hours_spent)).filter(
            TimeLog.task_id == self.id
        ).scalar()
        return total or 0
    
    @property
    def remaining_hours(self):
        """Calculate remaining hours."""
        return max(0, (self.estimated_hours or 0) - self.logged_hours)
    
    @property
    def calculated_completion(self):
        """Calculate completion percentage based on logged vs estimated hours."""
        if self.estimated_hours and self.estimated_hours > 0:
            percentage = (self.logged_hours / self.estimated_hours) * 100
            return min(100, int(percentage))  # Cap at 100%
        return self.completion_percentage or 0
    
    def is_overdue(self):
        """Check if task is past due date."""
        if self.due_date and self.status != TaskStatus.DONE.value:
            return self.due_date < get_ist_date()
        return False
    
    def __repr__(self):
        return f'<Task {self.title}>'


class Comment(db.Model):
    """
    Task comment model.
    
    Attributes:
        id: Primary key
        task_id: Parent task
        user_id: Comment author
        content: Comment text
        created_at: Creation timestamp
    """
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_now)
    
    def __repr__(self):
        return f'<Comment {self.id} on Task {self.task_id}>'


class TimeLog(db.Model):
    """
    Time log model for tracking effort on tasks.
    
    Attributes:
        id: Primary key
        task_id: Parent task
        user_id: User who logged time
        hours_spent: Hours worked
        description: Work description
        logged_date: Date when work was done
        created_at: Creation timestamp
    """
    __tablename__ = 'time_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hours_spent = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500))
    logged_date = db.Column(db.Date, default=get_ist_date)
    created_at = db.Column(db.DateTime, default=get_ist_now)
    
    # Relationship
    user = db.relationship('User', backref='time_logs')
    
    def __repr__(self):
        return f'<TimeLog {self.hours_spent}h on Task {self.task_id}>'


class TaskHistory(db.Model):
    """
    Task audit log for tracking changes.
    
    Attributes:
        id: Primary key
        task_id: Related task
        user_id: User who made the change
        action: Type of action (created, updated, status_changed, etc.)
        field_name: Field that was changed
        old_value: Previous value
        new_value: New value
        created_at: Timestamp of change
    """
    __tablename__ = 'task_history'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    field_name = db.Column(db.String(50))
    old_value = db.Column(db.String(500))
    new_value = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=get_ist_now)
    
    # Relationship
    user = db.relationship('User', backref='task_changes')
    
    def __repr__(self):
        return f'<TaskHistory {self.action} on Task {self.task_id}>'
