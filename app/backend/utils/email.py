"""
Email Utility Functions
Handles sending emails for password reset and notifications.
"""
from threading import Thread
from flask import current_app, render_template
from flask_mail import Message

from app import mail


def send_async_email(app, msg):
    """Send email asynchronously."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f'Failed to send email: {str(e)}')


def send_email(subject, recipients, text_body, html_body=None):
    """
    Send an email.
    
    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        text_body: Plain text email body
        html_body: HTML email body (optional)
    """
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    
    # Send email asynchronously to not block the request
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()


def send_password_reset_email(user):
    """
    Send password reset email to user.
    
    Args:
        user: User object to send reset email to
    """
    token = user.get_reset_password_token()
    send_email(
        subject='[EcoGTasks] Reset Your Password',
        recipients=[user.email],
        text_body=render_template('auth/email/reset_password.txt', user=user, token=token),
        html_body=render_template('auth/email/reset_password.html', user=user, token=token)
    )


def send_welcome_email(user):
    """
    Send welcome email to newly registered user.
    
    Args:
        user: User object to send welcome email to
    """
    send_email(
        subject='[EcoGTasks] Welcome to EcoGTasks!',
        recipients=[user.email],
        text_body=render_template('auth/email/welcome.txt', user=user),
        html_body=render_template('auth/email/welcome.html', user=user)
    )


def send_approval_email(user):
    """
    Send account approval notification email to user.
    
    Args:
        user: User object whose account was approved
    """
    send_email(
        subject='[EcoGTasks] Your Account Has Been Approved!',
        recipients=[user.email],
        text_body=render_template('auth/email/account_approved.txt', user=user),
        html_body=render_template('auth/email/account_approved.html', user=user)
    )


def send_rejection_email(user, reason=None):
    """
    Send account rejection notification email to user.
    
    Args:
        user: User object whose account was rejected
        reason: Optional reason for rejection
    """
    send_email(
        subject='[EcoGTasks] Account Registration Update',
        recipients=[user.email],
        text_body=render_template('auth/email/account_rejected.txt', user=user, reason=reason),
        html_body=render_template('auth/email/account_rejected.html', user=user, reason=reason)
    )
