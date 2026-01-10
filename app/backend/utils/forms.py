"""
WTForms Form Definitions
Provides form classes with CSRF protection and validation.
"""
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, TextAreaField, SelectField,
                     DateField, SubmitField, BooleanField, HiddenField,
                     DecimalField, IntegerField)
from wtforms.validators import (DataRequired, Email, Length, EqualTo,
                                 ValidationError, Optional, NumberRange)

from app.backend.models import User, UserRole, TaskStatus, TaskPriority


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """User registration form (Admin only)."""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
        (UserRole.EMPLOYEE.value, 'Employee'),
        (UserRole.MANAGER.value, 'Manager'),
        (UserRole.ADMIN.value, 'Admin')
    ], validators=[DataRequired()])
    submit = SubmitField('Register User')
    
    def validate_username(self, username):
        """Check if username is already taken."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email is already registered."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')


class PublicRegistrationForm(FlaskForm):
    """Public user registration form."""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Create Account')
    
    def validate_username(self, username):
        """Check if username is already taken."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email is already registered."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')


class ForgotPasswordForm(FlaskForm):
    """Forgot password form - request password reset."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    """Reset password form - set new password."""
    password = PasswordField('New Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')


class TaskForm(FlaskForm):
    """Task creation and editing form."""
    title = StringField('Title', validators=[
        DataRequired(message='Title is required'),
        Length(max=200, message='Title must be less than 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=5000, message='Description must be less than 5000 characters')
    ])
    status = SelectField('Status', choices=[
        (TaskStatus.TODO.value, 'To Do'),
        (TaskStatus.IN_PROGRESS.value, 'In Progress'),
        (TaskStatus.BLOCKED.value, 'Blocked'),
        (TaskStatus.DONE.value, 'Done')
    ], validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        (TaskPriority.LOW.value, 'Low'),
        (TaskPriority.MEDIUM.value, 'Medium'),
        (TaskPriority.HIGH.value, 'High')
    ], validators=[DataRequired()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[Optional()], format='%Y-%m-%d')
    estimated_hours = DecimalField('Estimated Hours', validators=[
        Optional(),
        NumberRange(min=0, max=9999, message='Hours must be between 0 and 9999')
    ], places=1)
    completion_percentage = IntegerField('Completion %', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Percentage must be between 0 and 100')
    ], default=0)
    submit = SubmitField('Save Task')
    
    def validate_due_date(self, due_date):
        """Validate due date is not in the past for new tasks."""
        if due_date.data and due_date.data < date.today():
            raise ValidationError('Due date cannot be in the past.')


class CommentForm(FlaskForm):
    """Task comment form with optional file attachments."""
    content = TextAreaField('Comment', validators=[
        Optional(),  # Made optional since attachments can be added without text
        Length(max=2000, message='Comment must be less than 2000 characters')
    ])
    # Note: File uploads are handled via request.files, not WTForms
    submit = SubmitField('Add Comment')


class ProjectForm(FlaskForm):
    """Project creation and editing form."""
    name = StringField('Project Name', validators=[
        DataRequired(message='Project name is required'),
        Length(max=100, message='Project name must be less than 100 characters')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=2000, message='Description must be less than 2000 characters')
    ])
    submit = SubmitField('Save Project')


class ProjectMemberForm(FlaskForm):
    """Form to add members to a project."""
    user_id = SelectField('Select User', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Member')


class TaskFilterForm(FlaskForm):
    """Task filtering form."""
    status = SelectField('Status', choices=[
        ('', 'All Statuses'),
        (TaskStatus.TODO.value, 'To Do'),
        (TaskStatus.IN_PROGRESS.value, 'In Progress'),
        (TaskStatus.BLOCKED.value, 'Blocked'),
        (TaskStatus.DONE.value, 'Done')
    ], validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('', 'All Priorities'),
        (TaskPriority.LOW.value, 'Low'),
        (TaskPriority.MEDIUM.value, 'Medium'),
        (TaskPriority.HIGH.value, 'High')
    ], validators=[Optional()])
    assigned_to = SelectField('Assigned To', coerce=int, validators=[Optional()])
    project_id = SelectField('Project', coerce=int, validators=[Optional()])
    search = StringField('Search', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Filter')


class ReassignTaskForm(FlaskForm):
    """Form to reassign a task."""
    assigned_to = SelectField('Reassign To', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Reassign')


class TimeLogForm(FlaskForm):
    """Form to log time spent on a task."""
    hours_spent = DecimalField('Hours Spent', validators=[
        DataRequired(message='Hours spent is required'),
        NumberRange(min=0.1, max=24, message='Hours must be between 0.1 and 24')
    ], places=1)
    description = StringField('Work Description', validators=[
        Optional(),
        Length(max=500, message='Description must be less than 500 characters')
    ])
    logged_date = DateField('Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Log Time')


class UpdateProgressForm(FlaskForm):
    """Form to update task completion percentage."""
    completion_percentage = IntegerField('Completion %', validators=[
        DataRequired(),
        NumberRange(min=0, max=100, message='Percentage must be between 0 and 100')
    ])
    submit = SubmitField('Update Progress')


class EmailConfigForm(FlaskForm):
    """Form to configure email settings."""
    os_type = SelectField('Operating System', choices=[
        ('auto', 'Auto Detect'),
        ('windows', 'Windows'),
        ('macos', 'macOS'),
        ('linux', 'Linux')
    ])
    mail_server = StringField('SMTP Server', validators=[
        DataRequired(message='SMTP server is required'),
        Length(max=255, message='Server must be less than 255 characters')
    ])
    mail_port = IntegerField('Port', validators=[
        DataRequired(message='Port is required'),
        NumberRange(min=1, max=65535, message='Port must be between 1 and 65535')
    ])
    mail_use_tls = BooleanField('Use TLS')
    mail_use_ssl = BooleanField('Use SSL')
    mail_username = StringField('Username/Email', validators=[
        DataRequired(message='Username is required'),
        Length(max=255, message='Username must be less than 255 characters')
    ])
    mail_password = PasswordField('Password/App Password', validators=[
        Optional(),
        Length(max=255, message='Password must be less than 255 characters')
    ])
    mail_default_sender = StringField('Default Sender Email', validators=[
        Optional(),
        Email(message='Please enter a valid email address'),
        Length(max=255)
    ])
    submit = SubmitField('Save Configuration')
