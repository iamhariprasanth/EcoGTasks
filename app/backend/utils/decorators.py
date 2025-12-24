"""
Custom Decorators for Role-Based Access Control
Provides reusable decorators for protecting routes based on user roles.
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user

from app.backend.models import UserRole


def admin_required(f):
    """
    Decorator to restrict access to admin users only.
    
    Usage:
        @admin_required
        def admin_only_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """
    Decorator to restrict access to manager or admin users.
    
    Usage:
        @manager_required
        def manager_only_route():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_manager_or_admin():
            flash('You do not have permission to access this page.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def project_access_required(f):
    """
    Decorator to verify user has access to the project.
    Expects 'project_id' in route parameters.
    
    Usage:
        @project_access_required
        def project_route(project_id):
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.backend.models import Project
        
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        project_id = kwargs.get('project_id')
        if project_id:
            project = Project.query.get_or_404(project_id)
            if not current_user.can_access_project(project):
                flash('You do not have access to this project.', 'danger')
                abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def task_access_required(f):
    """
    Decorator to verify user has access to the task.
    Expects 'task_id' in route parameters.
    Admin and managers can access all tasks in their projects.
    Employees can only access tasks assigned to them.
    
    Usage:
        @task_access_required
        def task_route(task_id):
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.backend.models import Task
        
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        task_id = kwargs.get('task_id')
        if task_id:
            task = Task.query.get_or_404(task_id)
            
            # Admin can access all tasks
            if current_user.is_admin():
                return f(*args, **kwargs)
            
            # Manager can access tasks in their projects
            if current_user.is_manager() and current_user.can_access_project(task.project):
                return f(*args, **kwargs)
            
            # Employee can only access their assigned tasks or tasks they created
            if task.assigned_to == current_user.id or task.created_by == current_user.id:
                return f(*args, **kwargs)
            
            # Check if user is member of the project
            if current_user.can_access_project(task.project):
                return f(*args, **kwargs)
            
            flash('You do not have access to this task.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function
