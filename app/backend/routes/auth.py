"""
Authentication Routes
Handles user login, logout, registration, and password reset.
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.backend.models import User, UserRole
from app.backend.utils.forms import (
    LoginForm, RegistrationForm, PublicRegistrationForm,
    ForgotPasswordForm, ResetPasswordForm
)
from app.backend.utils.decorators import admin_required
from app.backend.utils.email import send_password_reset_email, send_welcome_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    Redirects authenticated users to dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        # Verify credentials
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if account is approved by admin
        if not user.is_approved:
            flash('Your account is pending admin approval. You will receive an email once approved.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if account is active
        if not user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Log in the user
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        flash(f'Welcome back, {user.username}!', 'success')
        
        # Redirect to the requested page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/login.html', form=form, title='Sign In')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    User logout route.
    Clears session and redirects to login.
    """
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Public user registration route.
    Creates new user accounts with default Employee role.
    Account requires admin approval before login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = PublicRegistrationForm()
    
    if form.validate_on_submit():
        # Create new user with Employee role (pending approval)
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            role=UserRole.EMPLOYEE.value,
            is_approved=False  # Requires admin approval
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created and is pending admin approval. You will receive an email once approved.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html', form=form, title='Create Account')


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    """
    User registration route (Admin only).
    Creates new user accounts with any role.
    """
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {user.username} has been registered successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html', form=form, title='Register New User')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Forgot password route.
    Sends password reset email to user.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user:
            # Send password reset email
            try:
                if current_app.config.get('MAIL_USERNAME'):
                    send_password_reset_email(user)
                    flash('A password reset link has been sent to your email address.', 'info')
                else:
                    # If email not configured, show token directly (for development)
                    token = user.get_reset_password_token()
                    flash(f'Email not configured. Use this link to reset: /reset-password/{token}', 'warning')
            except Exception as e:
                current_app.logger.error(f'Failed to send reset email: {str(e)}')
                flash('Failed to send reset email. Please try again later.', 'danger')
        else:
            # Don't reveal if email exists or not (security)
            flash('If an account with that email exists, a password reset link has been sent.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form, title='Forgot Password')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Reset password route.
    Validates token and allows user to set new password.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    user = User.verify_reset_password_token(token)
    
    if not user:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Your password has been reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form, title='Reset Password')
