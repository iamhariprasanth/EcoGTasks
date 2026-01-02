"""
Dashboard Routes
Role-specific dashboards with relevant statistics and data.
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.backend.models import User, Task, Project, TaskStatus, TaskPriority, UserRole

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """
    Main dashboard route.
    Redirects to role-specific dashboard.
    """
    if current_user.is_admin():
        return redirect(url_for('dashboard.admin_dashboard'))
    elif current_user.is_manager():
        return redirect(url_for('dashboard.manager_dashboard'))
    else:
        return redirect(url_for('dashboard.employee_dashboard'))


@dashboard_bp.route('/dashboard/admin')
@login_required
def admin_dashboard():
    """
    Admin dashboard with system-wide statistics.
    Shows user count, task stats, and project overview.
    """
    if not current_user.is_admin():
        return redirect(url_for('dashboard.index'))
    
    # User statistics
    total_users = User.query.filter_by(is_approved=True).count()
    admin_count = User.query.filter_by(role=UserRole.ADMIN.value, is_approved=True).count()
    manager_count = User.query.filter_by(role=UserRole.MANAGER.value, is_approved=True).count()
    employee_count = User.query.filter_by(role=UserRole.EMPLOYEE.value, is_approved=True).count()
    
    # Pending approvals count
    pending_approvals = User.query.filter_by(is_approved=False).count()
    
    # Task statistics
    total_tasks = Task.query.count()
    todo_count = Task.query.filter_by(status=TaskStatus.TODO.value).count()
    in_progress_count = Task.query.filter_by(status=TaskStatus.IN_PROGRESS.value).count()
    done_count = Task.query.filter_by(status=TaskStatus.DONE.value).count()
    
    # Priority breakdown
    high_priority = Task.query.filter_by(priority=TaskPriority.HIGH.value).count()
    medium_priority = Task.query.filter_by(priority=TaskPriority.MEDIUM.value).count()
    low_priority = Task.query.filter_by(priority=TaskPriority.LOW.value).count()
    
    # Project statistics
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(is_active=True).count()
    
    # Recent tasks
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(5).all()
    
    # Recent users (approved only)
    recent_users = User.query.filter_by(is_approved=True).order_by(User.created_at.desc()).limit(5).all()
    
    return render_template(
        'dashboard/admin.html',
        title='Admin Dashboard',
        total_users=total_users,
        admin_count=admin_count,
        manager_count=manager_count,
        employee_count=employee_count,
        pending_approvals=pending_approvals,
        total_tasks=total_tasks,
        todo_count=todo_count,
        in_progress_count=in_progress_count,
        done_count=done_count,
        high_priority=high_priority,
        medium_priority=medium_priority,
        low_priority=low_priority,
        total_projects=total_projects,
        active_projects=active_projects,
        recent_tasks=recent_tasks,
        recent_users=recent_users
    )


@dashboard_bp.route('/dashboard/manager')
@login_required
def manager_dashboard():
    """
    Manager dashboard with team workload.
    Shows tasks in managed projects and team statistics.
    """
    if not current_user.is_manager_or_admin():
        return redirect(url_for('dashboard.employee_dashboard'))
    
    # Get projects where user is a member or owner
    user_projects = current_user.projects + list(current_user.created_projects)
    project_ids = [p.id for p in user_projects]
    
    # Task statistics for managed projects
    managed_tasks = Task.query.filter(Task.project_id.in_(project_ids)) if project_ids else Task.query.filter(False)
    
    total_tasks = managed_tasks.count() if project_ids else 0
    todo_count = managed_tasks.filter(Task.status == TaskStatus.TODO.value).count() if project_ids else 0
    in_progress_count = managed_tasks.filter(Task.status == TaskStatus.IN_PROGRESS.value).count() if project_ids else 0
    done_count = managed_tasks.filter(Task.status == TaskStatus.DONE.value).count() if project_ids else 0
    
    # Team members in projects
    team_members = set()
    for project in user_projects:
        for member in project.members:
            team_members.add(member)
    
    # Workload per team member
    team_workload = []
    for member in team_members:
        member_tasks = Task.query.filter(
            Task.assigned_to == member.id,
            Task.project_id.in_(project_ids)
        ).count() if project_ids else 0
        team_workload.append({
            'user': member,
            'task_count': member_tasks
        })
    
    # Sort by task count descending
    team_workload.sort(key=lambda x: x['task_count'], reverse=True)
    
    # Recent tasks in managed projects
    recent_tasks = managed_tasks.order_by(Task.updated_at.desc()).limit(10).all() if project_ids else []
    
    return render_template(
        'dashboard/manager.html',
        title='Manager Dashboard',
        projects=user_projects,
        total_tasks=total_tasks,
        todo_count=todo_count,
        in_progress_count=in_progress_count,
        done_count=done_count,
        team_workload=team_workload,
        recent_tasks=recent_tasks
    )


@dashboard_bp.route('/dashboard/employee')
@login_required
def employee_dashboard():
    """
    Employee dashboard with assigned tasks.
    Shows personal task summary and upcoming deadlines.
    """
    # Get assigned tasks
    assigned_tasks = Task.query.filter_by(assigned_to=current_user.id)
    
    # Task statistics
    total_assigned = assigned_tasks.count()
    todo_count = assigned_tasks.filter(Task.status == TaskStatus.TODO.value).count()
    in_progress_count = assigned_tasks.filter(Task.status == TaskStatus.IN_PROGRESS.value).count()
    blocked_count = assigned_tasks.filter(Task.status == TaskStatus.BLOCKED.value).count()
    done_count = assigned_tasks.filter(Task.status == TaskStatus.DONE.value).count()
    
    # Incomplete tasks count (for weekly status)
    incomplete_count = todo_count + in_progress_count + blocked_count
    
    # High priority tasks
    high_priority_tasks = assigned_tasks.filter(
        Task.priority == TaskPriority.HIGH.value,
        Task.status != TaskStatus.DONE.value
    ).order_by(Task.due_date.asc()).all()
    
    # Upcoming deadlines (tasks with due dates, sorted by date)
    from datetime import date
    upcoming_tasks = assigned_tasks.filter(
        Task.due_date != None,
        Task.status != TaskStatus.DONE.value
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Recent tasks
    recent_tasks = assigned_tasks.order_by(Task.updated_at.desc()).limit(10).all()
    
    # User's projects
    user_projects = current_user.projects
    
    # Current week tasks (incomplete only)
    current_week_tasks = {
        'in_progress': assigned_tasks.filter(Task.status == TaskStatus.IN_PROGRESS.value).all(),
        'blocked': assigned_tasks.filter(Task.status == TaskStatus.BLOCKED.value).all(),
        'todo': assigned_tasks.filter(Task.status == TaskStatus.TODO.value).all()
    }
    
    return render_template(
        'dashboard/employee.html',
        title='My Dashboard',
        total_assigned=total_assigned,
        todo_count=todo_count,
        in_progress_count=in_progress_count,
        blocked_count=blocked_count,
        done_count=done_count,
        incomplete_count=incomplete_count,
        high_priority_tasks=high_priority_tasks,
        upcoming_tasks=upcoming_tasks,
        recent_tasks=recent_tasks,
        projects=user_projects,
        current_week_tasks=current_week_tasks
    )
