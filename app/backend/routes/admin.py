"""
Admin Routes
User management and system administration.
"""
from datetime import timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user

from app import db
from app.backend.models import User, Task, Project, UserRole, TaskStatus, get_ist_now, get_ist_date
from app.backend.utils.decorators import admin_required
from app.backend.utils.email import send_approval_email, send_rejection_email, send_weekly_task_status_email

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """
    Admin panel home - redirects to dashboard.
    """
    return redirect(url_for('dashboard.admin_dashboard'))


@admin_bp.route('/pending-users')
@login_required
@admin_required
def pending_users():
    """
    List users pending approval.
    """
    page = request.args.get('page', 1, type=int)
    
    # Get users who are not approved yet
    pagination = User.query.filter_by(is_approved=False).order_by(
        User.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    pending_list = pagination.items
    pending_count = User.query.filter_by(is_approved=False).count()
    
    return render_template(
        'admin/pending_users.html',
        title='Pending Approvals',
        users=pending_list,
        pagination=pagination,
        pending_count=pending_count
    )


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    """
    Approve a pending user account.
    """
    user = User.query.get_or_404(user_id)
    
    if user.is_approved:
        flash(f'User {user.username} is already approved.', 'info')
        return redirect(url_for('admin.pending_users'))
    
    user.is_approved = True
    db.session.commit()
    
    # Send approval email
    try:
        if current_app.config.get('MAIL_USERNAME'):
            send_approval_email(user)
            flash(f'User {user.username} has been approved and notified via email.', 'success')
        else:
            flash(f'User {user.username} has been approved. (Email not configured)', 'success')
    except Exception as e:
        current_app.logger.error(f'Failed to send approval email: {str(e)}')
        flash(f'User {user.username} has been approved but email notification failed.', 'warning')
    
    return redirect(url_for('admin.pending_users'))


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    """
    Reject and delete a pending user account.
    """
    user = User.query.get_or_404(user_id)
    
    if user.is_approved:
        flash(f'Cannot reject an already approved user. Use deactivate instead.', 'danger')
        return redirect(url_for('admin.users'))
    
    username = user.username
    email = user.email
    reason = request.form.get('reason', '')
    
    # Send rejection email before deleting
    try:
        if current_app.config.get('MAIL_USERNAME'):
            send_rejection_email(user, reason)
    except Exception as e:
        current_app.logger.error(f'Failed to send rejection email: {str(e)}')
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been rejected and removed.', 'success')
    
    return redirect(url_for('admin.pending_users'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    User management page with pagination.
    """
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    search = request.args.get('search', '')
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    users_list = pagination.items
    
    return render_template(
        'admin/users.html',
        title='User Management',
        users=users_list,
        pagination=pagination,
        role_filter=role_filter,
        search=search,
        roles=UserRole
    )


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """
    View user details.
    """
    user = User.query.get_or_404(user_id)
    
    # Get user statistics
    assigned_tasks = user.assigned_tasks.count()
    created_tasks = user.created_tasks.count()
    projects_count = len(user.projects)
    
    # Recent activity
    recent_tasks = user.assigned_tasks.order_by(Task.updated_at.desc()).limit(5).all()
    
    return render_template(
        'admin/user_detail.html',
        title=f'User: {user.username}',
        user=user,
        assigned_tasks=assigned_tasks,
        created_tasks=created_tasks,
        projects_count=projects_count,
        recent_tasks=recent_tasks
    )


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """
    Activate or deactivate a user account.
    """
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating yourself
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """
    Change a user's role.
    """
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role not in [r.value for r in UserRole]:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.view_user', user_id=user_id))
    
    # Prevent changing your own role
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'danger')
        return redirect(url_for('admin.view_user', user_id=user_id))
    
    old_role = user.role
    user.role = new_role
    db.session.commit()
    
    flash(f'User {user.username} role changed from {old_role} to {new_role}.', 'success')
    
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Delete a user account.
    Warning: This will also affect related tasks and comments.
    """
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    username = user.username
    
    # Reassign or handle tasks before deletion
    # For now, we'll just unassign tasks
    Task.query.filter_by(assigned_to=user.id).update({'assigned_to': None})
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been deleted. Their assigned tasks have been unassigned.', 'success')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """
    Reset a user's password to a default value.
    """
    user = User.query.get_or_404(user_id)
    
    # Generate a temporary password
    temp_password = 'TempPass123!'
    user.set_password(temp_password)
    db.session.commit()
    
    flash(f'Password for {user.username} has been reset to: {temp_password}', 'warning')
    
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/send-weekly-status', methods=['POST'])
@login_required
@admin_required
def send_weekly_status():
    """
    Send weekly task status email to all active users.
    """
    # Calculate current week (Monday to Sunday) in IST
    today = get_ist_date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get all active and approved users
    users = User.query.filter_by(is_active=True, is_approved=True).all()
    sent_count = 0
    
    for user in users:
        # Get user's incomplete tasks (not done)
        user_tasks = Task.query.filter(
            Task.assigned_to == user.id,
            Task.status != TaskStatus.DONE.value
        ).all()
        
        if user_tasks:
            # Categorize tasks
            tasks = {
                'in_progress': [t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS.value],
                'blocked': [t for t in user_tasks if t.status == TaskStatus.BLOCKED.value],
                'todo': [t for t in user_tasks if t.status == TaskStatus.TODO.value]
            }
            
            # Only send if user has any incomplete tasks
            if any(tasks.values()):
                send_weekly_task_status_email(user, tasks, week_start, week_end)
                sent_count += 1
    
    flash(f'Weekly status emails sent to {sent_count} users.', 'success')
    return redirect(url_for('dashboard.admin_dashboard'))


@admin_bp.route('/send-status-to-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def send_status_to_user(user_id):
    """
    Send task status email to a specific user.
    """
    user = User.query.get_or_404(user_id)
    
    # Calculate current week in IST
    today = get_ist_date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get user's incomplete tasks
    user_tasks = Task.query.filter(
        Task.assigned_to == user.id,
        Task.status != TaskStatus.DONE.value
    ).all()
    
    if user_tasks:
        tasks = {
            'in_progress': [t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS.value],
            'blocked': [t for t in user_tasks if t.status == TaskStatus.BLOCKED.value],
            'todo': [t for t in user_tasks if t.status == TaskStatus.TODO.value]
        }
        
        send_weekly_task_status_email(user, tasks, week_start, week_end)
        flash(f'Task status email sent to {user.username}.', 'success')
    else:
        flash(f'{user.username} has no incomplete tasks.', 'info')
    
    return redirect(url_for('admin.view_user', user_id=user_id))


@admin_bp.route('/email-notifications')
@login_required
@admin_required
def email_notifications():
    """
    Email notifications dashboard for managing and sending task status emails.
    """
    # Get all users with their task counts
    users = User.query.filter_by(is_active=True, is_approved=True).order_by(User.username).all()
    
    user_task_summary = []
    for user in users:
        # Get incomplete tasks count
        incomplete_tasks = Task.query.filter(
            Task.assigned_to == user.id,
            Task.status != TaskStatus.DONE.value
        ).all()
        
        todo_count = sum(1 for t in incomplete_tasks if t.status == TaskStatus.TODO.value)
        in_progress_count = sum(1 for t in incomplete_tasks if t.status == TaskStatus.IN_PROGRESS.value)
        blocked_count = sum(1 for t in incomplete_tasks if t.status == TaskStatus.BLOCKED.value)
        
        user_task_summary.append({
            'user': user,
            'total_incomplete': len(incomplete_tasks),
            'todo': todo_count,
            'in_progress': in_progress_count,
            'blocked': blocked_count
        })
    
    # Sort by incomplete tasks (most first)
    user_task_summary.sort(key=lambda x: x['total_incomplete'], reverse=True)
    
    # Email configuration status
    email_config = {
        'server': current_app.config.get('MAIL_SERVER', 'Not configured'),
        'port': current_app.config.get('MAIL_PORT', 'Not configured'),
        'use_tls': current_app.config.get('MAIL_USE_TLS', False),
        'username': current_app.config.get('MAIL_USERNAME', 'Not configured'),
        'configured': bool(current_app.config.get('MAIL_USERNAME') and current_app.config.get('MAIL_PASSWORD'))
    }
    
    # Calculate current week in IST
    today = get_ist_date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    return render_template(
        'admin/email_notifications.html',
        title='Email Notifications',
        user_task_summary=user_task_summary,
        email_config=email_config,
        week_start=week_start,
        week_end=week_end,
        total_users_with_tasks=sum(1 for u in user_task_summary if u['total_incomplete'] > 0)
    )


@admin_bp.route('/send-status-selected', methods=['POST'])
@login_required
@admin_required
def send_status_selected():
    """
    Send task status email to selected users.
    """
    selected_users = request.form.getlist('selected_users')
    
    if not selected_users:
        flash('No users selected.', 'warning')
        return redirect(url_for('admin.email_notifications'))
    
    # Calculate current week in IST
    today = get_ist_date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    sent_count = 0
    for user_id in selected_users:
        user = User.query.get(int(user_id))
        if user:
            user_tasks = Task.query.filter(
                Task.assigned_to == user.id,
                Task.status != TaskStatus.DONE.value
            ).all()
            
            if user_tasks:
                tasks = {
                    'in_progress': [t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS.value],
                    'blocked': [t for t in user_tasks if t.status == TaskStatus.BLOCKED.value],
                    'todo': [t for t in user_tasks if t.status == TaskStatus.TODO.value]
                }
                send_weekly_task_status_email(user, tasks, week_start, week_end)
                sent_count += 1
    
    flash(f'Task status emails sent to {sent_count} user(s).', 'success')
    return redirect(url_for('admin.email_notifications'))
