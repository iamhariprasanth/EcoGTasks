"""
Dashboard Routes
Role-specific dashboards with relevant statistics and data.
"""
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.backend.models import User, Task, Project, TaskStatus, TaskPriority, UserRole, get_ist_now, get_ist_date

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
    Shows user count, task stats, project overview, and burndown chart.
    Supports date range filtering via start_date and end_date query parameters.
    """
    if not current_user.is_admin():
        return redirect(url_for('dashboard.index'))
    
    # Get date filter parameters
    today = get_ist_date()
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    # Parse dates or use defaults (last 30 days)
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today - timedelta(days=30)
    except ValueError:
        start_date = today - timedelta(days=30)
    
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
    except ValueError:
        end_date = today
    
    # Ensure end_date is not before start_date
    if end_date < start_date:
        end_date = start_date
    
    # User statistics (not filtered by date)
    total_users = User.query.filter_by(is_approved=True).count()
    admin_count = User.query.filter_by(role=UserRole.ADMIN.value, is_approved=True).count()
    manager_count = User.query.filter_by(role=UserRole.MANAGER.value, is_approved=True).count()
    employee_count = User.query.filter_by(role=UserRole.EMPLOYEE.value, is_approved=True).count()
    
    # Pending approvals count
    pending_approvals = User.query.filter_by(is_approved=False).count()
    
    # Base query for tasks within date range (created within the period)
    date_filtered_tasks = Task.query.filter(
        db.func.date(Task.created_at) >= start_date,
        db.func.date(Task.created_at) <= end_date
    )
    
    # Task statistics (filtered by date range)
    total_tasks = date_filtered_tasks.count()
    todo_count = date_filtered_tasks.filter(Task.status == TaskStatus.TODO.value).count()
    in_progress_count = date_filtered_tasks.filter(Task.status == TaskStatus.IN_PROGRESS.value).count()
    blocked_count = date_filtered_tasks.filter(Task.status == TaskStatus.BLOCKED.value).count()
    done_count = date_filtered_tasks.filter(Task.status == TaskStatus.DONE.value).count()
    
    # Due tasks (tasks with due date in the past that are not done, within date range)
    overdue_count = date_filtered_tasks.filter(
        Task.due_date < today,
        Task.status != TaskStatus.DONE.value
    ).count()
    
    # Priority breakdown (filtered by date)
    high_priority = date_filtered_tasks.filter(Task.priority == TaskPriority.HIGH.value).count()
    medium_priority = date_filtered_tasks.filter(Task.priority == TaskPriority.MEDIUM.value).count()
    low_priority = date_filtered_tasks.filter(Task.priority == TaskPriority.LOW.value).count()
    
    # Project statistics
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(is_active=True).count()
    
    # Project completion data (filtered by date range)
    projects = Project.query.filter_by(is_active=True).all()
    project_stats = []
    for project in projects:
        # Filter tasks by date range for each project
        project_tasks = project.tasks.filter(
            db.func.date(Task.created_at) >= start_date,
            db.func.date(Task.created_at) <= end_date
        )
        project_total = project_tasks.count()
        project_done = project_tasks.filter(Task.status == TaskStatus.DONE.value).count()
        project_in_progress = project_tasks.filter(Task.status == TaskStatus.IN_PROGRESS.value).count()
        project_todo = project_tasks.filter(Task.status == TaskStatus.TODO.value).count()
        project_blocked = project_tasks.filter(Task.status == TaskStatus.BLOCKED.value).count()
        completion_percent = round((project_done / project_total * 100), 1) if project_total > 0 else 0
        project_stats.append({
            'id': project.id,
            'name': project.name,
            'total': project_total,
            'done': project_done,
            'in_progress': project_in_progress,
            'todo': project_todo,
            'blocked': project_blocked,
            'completion': completion_percent
        })
    
    # Sort projects by completion percentage
    project_stats.sort(key=lambda x: x['completion'], reverse=True)
    
    # Burndown chart data (for the selected date range)
    burndown_data = []
    date_range_days = (end_date - start_date).days + 1
    # Limit to max 30 data points for readability
    step = max(1, date_range_days // 30)
    
    current_date = start_date
    while current_date <= end_date:
        # Count tasks that were created on or before this date and not yet completed by this date
        tasks_remaining = Task.query.filter(
            db.func.date(Task.created_at) >= start_date,
            db.func.date(Task.created_at) <= current_date,
            db.or_(
                Task.status != TaskStatus.DONE.value,
                db.and_(
                    Task.status == TaskStatus.DONE.value,
                    db.func.date(Task.updated_at) > current_date
                )
            )
        ).count()
        
        # Tasks completed on or before this date (within the date range)
        tasks_completed = Task.query.filter(
            db.func.date(Task.created_at) >= start_date,
            Task.status == TaskStatus.DONE.value,
            db.func.date(Task.updated_at) <= current_date
        ).count()
        
        burndown_data.append({
            'date': current_date.strftime('%b %d'),
            'remaining': tasks_remaining,
            'completed': tasks_completed
        })
        current_date += timedelta(days=step)
    
    # Ensure we include the end date
    if burndown_data and burndown_data[-1]['date'] != end_date.strftime('%b %d'):
        tasks_remaining = Task.query.filter(
            db.func.date(Task.created_at) >= start_date,
            db.func.date(Task.created_at) <= end_date,
            db.or_(
                Task.status != TaskStatus.DONE.value,
                db.and_(
                    Task.status == TaskStatus.DONE.value,
                    db.func.date(Task.updated_at) > end_date
                )
            )
        ).count()
        tasks_completed = Task.query.filter(
            db.func.date(Task.created_at) >= start_date,
            Task.status == TaskStatus.DONE.value,
            db.func.date(Task.updated_at) <= end_date
        ).count()
        burndown_data.append({
            'date': end_date.strftime('%b %d'),
            'remaining': tasks_remaining,
            'completed': tasks_completed
        })
    
    # Overall completion percentage
    overall_completion = round((done_count / total_tasks * 100), 1) if total_tasks > 0 else 0
    
    # Recent tasks (within date range)
    recent_tasks = date_filtered_tasks.order_by(Task.created_at.desc()).limit(5).all()
    
    # Recent users (approved only, not filtered by date)
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
        blocked_count=blocked_count,
        done_count=done_count,
        overdue_count=overdue_count,
        high_priority=high_priority,
        medium_priority=medium_priority,
        low_priority=low_priority,
        total_projects=total_projects,
        active_projects=active_projects,
        project_stats=project_stats,
        burndown_data=burndown_data,
        overall_completion=overall_completion,
        recent_tasks=recent_tasks,
        recent_users=recent_users,
        start_date=start_date,
        end_date=end_date,
        today=today,
        # Quick filter dates
        date_7_days_ago=(today - timedelta(days=7)).strftime('%Y-%m-%d'),
        date_30_days_ago=(today - timedelta(days=30)).strftime('%Y-%m-%d'),
        date_90_days_ago=(today - timedelta(days=90)).strftime('%Y-%m-%d'),
        today_str=today.strftime('%Y-%m-%d')
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
