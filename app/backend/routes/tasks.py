"""
Task Routes
Complete CRUD operations for tasks with comments and history.
"""
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response
from flask_login import login_required, current_user

from app import db
from app.backend.models import Task, Project, User, Comment, TaskHistory, TaskStatus, TaskPriority, TimeLog
from app.backend.utils.forms import TaskForm, CommentForm, TaskFilterForm, ReassignTaskForm, TimeLogForm, UpdateProgressForm
from app.backend.utils.decorators import task_access_required, project_access_required

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


def log_task_history(task, user, action, field_name=None, old_value=None, new_value=None):
    """Helper function to log task changes."""
    history = TaskHistory(
        task_id=task.id,
        user_id=user.id,
        action=action,
        field_name=field_name,
        old_value=str(old_value) if old_value else None,
        new_value=str(new_value) if new_value else None
    )
    db.session.add(history)


@tasks_bp.route('/')
@login_required
def list_tasks():
    """
    List all tasks with filtering and pagination.
    Admins see all tasks, managers see project tasks, employees see assigned tasks.
    """
    form = TaskFilterForm()
    
    # Populate filter choices
    form.assigned_to.choices = [(0, 'All Users')] + [
        (u.id, u.username) for u in User.query.filter_by(is_active=True).order_by(User.username).all()
    ]
    form.project_id.choices = [(0, 'All Projects')] + [
        (p.id, p.name) for p in Project.query.filter_by(is_active=True).order_by(Project.name).all()
    ]
    
    # Base query based on user role
    if current_user.is_admin():
        query = Task.query
    elif current_user.is_manager():
        # Manager sees tasks in their projects
        project_ids = [p.id for p in current_user.projects] + [p.id for p in current_user.created_projects]
        query = Task.query.filter(Task.project_id.in_(project_ids)) if project_ids else Task.query.filter(False)
    else:
        # Employee sees only assigned tasks or tasks they created
        query = Task.query.filter(
            (Task.assigned_to == current_user.id) | (Task.created_by == current_user.id)
        )
    
    # Apply filters from request args
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    assigned_to = request.args.get('assigned_to', 0, type=int)
    project_id = request.args.get('project_id', 0, type=int)
    search = request.args.get('search', '')
    
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if search:
        query = query.filter(Task.title.ilike(f'%{search}%'))
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.order_by(Task.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    tasks = pagination.items
    
    return render_template(
        'tasks/list.html',
        title='Tasks',
        tasks=tasks,
        pagination=pagination,
        form=form,
        current_filters={
            'status': status,
            'priority': priority,
            'assigned_to': assigned_to,
            'project_id': project_id,
            'search': search
        }
    )


@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """
    Create a new task.
    """
    form = TaskForm()
    
    # Populate choices
    if current_user.is_admin():
        projects = Project.query.filter_by(is_active=True).all()
    else:
        projects = current_user.projects + list(current_user.created_projects)
    
    form.project_id.choices = [(p.id, p.name) for p in projects]
    form.assigned_to.choices = [(0, 'Unassigned')] + [
        (u.id, u.username) for u in User.query.filter_by(is_active=True).order_by(User.username).all()
    ]
    
    if not projects:
        flash('You need to be a member of at least one project to create tasks.', 'warning')
        return redirect(url_for('projects.list_projects'))
    
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            priority=form.priority.data,
            assigned_to=form.assigned_to.data if form.assigned_to.data else None,
            created_by=current_user.id,
            project_id=form.project_id.data,
            due_date=form.due_date.data
        )
        
        db.session.add(task)
        db.session.flush()  # Get task ID
        
        # Log creation
        log_task_history(task, current_user, 'created')
        
        db.session.commit()
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    return render_template('tasks/form.html', form=form, title='Create Task', is_edit=False)


@tasks_bp.route('/<int:task_id>')
@login_required
@task_access_required
def view_task(task_id):
    """
    View task details with comments and history.
    """
    task = Task.query.get_or_404(task_id)
    comment_form = CommentForm()
    reassign_form = ReassignTaskForm()
    time_log_form = TimeLogForm()
    progress_form = UpdateProgressForm()
    
    # Set default date for time log
    time_log_form.logged_date.data = date.today()
    
    # Populate reassign choices
    reassign_form.assigned_to.choices = [(0, 'Unassigned')] + [
        (u.id, u.username) for u in User.query.filter_by(is_active=True).order_by(User.username).all()
    ]
    
    # Get comments, history, and time logs
    comments = Comment.query.filter_by(task_id=task_id).order_by(Comment.created_at.desc()).all()
    history = TaskHistory.query.filter_by(task_id=task_id).order_by(TaskHistory.created_at.desc()).all()
    time_logs = TimeLog.query.filter_by(task_id=task_id).order_by(TimeLog.created_at.desc()).all()
    
    return render_template(
        'tasks/detail.html',
        title=task.title,
        task=task,
        comment_form=comment_form,
        reassign_form=reassign_form,
        time_log_form=time_log_form,
        progress_form=progress_form,
        comments=comments,
        history=history,
        time_logs=time_logs,
        TaskStatus=TaskStatus
    )


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@task_access_required
def edit_task(task_id):
    """
    Edit an existing task.
    """
    task = Task.query.get_or_404(task_id)
    form = TaskForm(obj=task)
    
    # Populate choices
    if current_user.is_admin():
        projects = Project.query.filter_by(is_active=True).all()
    else:
        projects = current_user.projects + list(current_user.created_projects)
    
    form.project_id.choices = [(p.id, p.name) for p in projects]
    form.assigned_to.choices = [(0, 'Unassigned')] + [
        (u.id, u.username) for u in User.query.filter_by(is_active=True).order_by(User.username).all()
    ]
    
    if form.validate_on_submit():
        # Track changes for history
        changes = []
        
        if task.title != form.title.data:
            changes.append(('title', task.title, form.title.data))
        if task.status != form.status.data:
            changes.append(('status', task.status, form.status.data))
        if task.priority != form.priority.data:
            changes.append(('priority', task.priority, form.priority.data))
        if task.assigned_to != (form.assigned_to.data if form.assigned_to.data else None):
            old_assignee = User.query.get(task.assigned_to).username if task.assigned_to else 'Unassigned'
            new_assignee = User.query.get(form.assigned_to.data).username if form.assigned_to.data else 'Unassigned'
            changes.append(('assigned_to', old_assignee, new_assignee))
        
        # Update task
        task.title = form.title.data
        task.description = form.description.data
        task.status = form.status.data
        task.priority = form.priority.data
        task.assigned_to = form.assigned_to.data if form.assigned_to.data else None
        task.project_id = form.project_id.data
        task.due_date = form.due_date.data
        
        # Log changes
        for field, old_val, new_val in changes:
            log_task_history(task, current_user, 'updated', field, old_val, new_val)
        
        db.session.commit()
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks.view_task', task_id=task.id))
    
    # Pre-populate form for GET request
    if request.method == 'GET':
        form.assigned_to.data = task.assigned_to or 0
    
    return render_template('tasks/form.html', form=form, title='Edit Task', is_edit=True, task=task)


@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
@task_access_required
def delete_task(task_id):
    """
    Delete a task.
    """
    task = Task.query.get_or_404(task_id)
    
    # Only admin, manager, or task creator can delete
    if not (current_user.is_admin() or current_user.is_manager() or task.created_by == current_user.id):
        flash('You do not have permission to delete this task.', 'danger')
        abort(403)
    
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    
    flash('Task deleted successfully.', 'success')
    return redirect(url_for('projects.view_project', project_id=project_id))


@tasks_bp.route('/<int:task_id>/comment', methods=['POST'])
@login_required
@task_access_required
def add_comment(task_id):
    """
    Add a comment to a task.
    """
    task = Task.query.get_or_404(task_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(
            task_id=task_id,
            user_id=current_user.id,
            content=form.content.data
        )
        db.session.add(comment)
        
        # Log comment addition
        log_task_history(task, current_user, 'commented')
        
        db.session.commit()
        flash('Comment added successfully!', 'success')
    else:
        flash('Comment cannot be empty.', 'danger')
    
    return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/<int:task_id>/reassign', methods=['POST'])
@login_required
@task_access_required
def reassign_task(task_id):
    """
    Reassign a task to another user.
    """
    task = Task.query.get_or_404(task_id)
    form = ReassignTaskForm()
    
    form.assigned_to.choices = [(0, 'Unassigned')] + [
        (u.id, u.username) for u in User.query.filter_by(is_active=True).order_by(User.username).all()
    ]
    
    if form.validate_on_submit():
        old_assignee = User.query.get(task.assigned_to).username if task.assigned_to else 'Unassigned'
        new_assignee_id = form.assigned_to.data if form.assigned_to.data else None
        new_assignee = User.query.get(new_assignee_id).username if new_assignee_id else 'Unassigned'
        
        task.assigned_to = new_assignee_id
        
        # Log reassignment
        log_task_history(task, current_user, 'reassigned', 'assigned_to', old_assignee, new_assignee)
        
        db.session.commit()
        flash(f'Task reassigned to {new_assignee}.', 'success')
    else:
        flash('Error reassigning task.', 'danger')
    
    return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/<int:task_id>/status/<status>', methods=['POST'])
@login_required
@task_access_required
def update_status(task_id, status):
    """
    Quick status update for a task.
    """
    task = Task.query.get_or_404(task_id)
    
    valid_statuses = [s.value for s in TaskStatus]
    if status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('tasks.view_task', task_id=task_id))
    
    old_status = task.status
    task.status = status
    
    # Auto-update completion percentage based on status
    if status == TaskStatus.DONE.value:
        task.completion_percentage = 100
    elif status == TaskStatus.TODO.value:
        task.completion_percentage = 0
    
    # Log status change
    log_task_history(task, current_user, 'status_changed', 'status', old_status, status)
    
    db.session.commit()
    flash(f'Task status updated to {status}.', 'success')
    
    return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/<int:task_id>/log-time', methods=['POST'])
@login_required
@task_access_required
def log_time(task_id):
    """
    Log time spent on a task.
    """
    task = Task.query.get_or_404(task_id)
    form = TimeLogForm()
    
    if form.validate_on_submit():
        time_log = TimeLog(
            task_id=task_id,
            user_id=current_user.id,
            hours_spent=float(form.hours_spent.data),
            description=form.description.data,
            logged_date=form.logged_date.data or date.today()
        )
        db.session.add(time_log)
        
        # Log to history
        log_task_history(task, current_user, 'logged_time', 'hours', None, f'{form.hours_spent.data}h')
        
        db.session.commit()
        flash(f'Logged {form.hours_spent.data} hours successfully.', 'success')
    else:
        flash('Error logging time. Please check your input.', 'danger')
    
    return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/<int:task_id>/update-progress', methods=['POST'])
@login_required
@task_access_required
def update_progress(task_id):
    """
    Update task completion percentage.
    """
    task = Task.query.get_or_404(task_id)
    form = UpdateProgressForm()
    
    if form.validate_on_submit():
        old_percentage = task.completion_percentage or 0
        new_percentage = form.completion_percentage.data
        task.completion_percentage = new_percentage
        
        # Auto-update status based on completion
        if new_percentage == 100 and task.status != TaskStatus.DONE.value:
            old_status = task.status
            task.status = TaskStatus.DONE.value
            log_task_history(task, current_user, 'status_changed', 'status', old_status, TaskStatus.DONE.value)
        elif new_percentage > 0 and new_percentage < 100 and task.status == TaskStatus.TODO.value:
            old_status = task.status
            task.status = TaskStatus.IN_PROGRESS.value
            log_task_history(task, current_user, 'status_changed', 'status', old_status, TaskStatus.IN_PROGRESS.value)
        
        # Log progress change
        log_task_history(task, current_user, 'progress_updated', 'completion', f'{old_percentage}%', f'{new_percentage}%')
        
        db.session.commit()
        flash(f'Progress updated to {new_percentage}%.', 'success')
    else:
        flash('Error updating progress. Please enter a value between 0 and 100.', 'danger')
    
    return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/<int:task_id>/download-ics')
@login_required
@task_access_required
def download_ics(task_id):
    """
    Generate and download an ICS calendar file for the task.
    Works with Apple Calendar, Outlook Desktop, Google Calendar, and other calendar apps.
    """
    task = Task.query.get_or_404(task_id)
    
    if not task.due_date:
        flash('This task does not have a due date set.', 'warning')
        return redirect(url_for('tasks.view_task', task_id=task_id))
    
    # Generate unique ID for the event
    uid = f"task-{task.id}@ecog-tasks"
    
    # Format dates for ICS (YYYYMMDD for all-day events)
    event_date = task.due_date.strftime('%Y%m%d')
    # End date should be the next day for all-day events
    from datetime import timedelta
    end_date = (task.due_date + timedelta(days=1)).strftime('%Y%m%d')
    
    # Current timestamp for DTSTAMP
    dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    # Build description
    description_parts = [
        f"Task: {task.title}",
        f"Project: {task.project.name}",
        f"Priority: {task.priority}",
        f"Status: {task.status}"
    ]
    if task.assignee:
        description_parts.append(f"Assigned to: {task.assignee.username}")
    if task.description:
        description_parts.append(f"\\nDescription:\\n{task.description}")
    
    # Escape special characters for ICS format
    description = "\\n".join(description_parts)
    description = description.replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;')
    
    summary = task.title.replace(',', '\\,').replace(';', '\\;')
    
    # Build ICS content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//EcoGTasks//Task Management//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART;VALUE=DATE:{event_date}
DTEND;VALUE=DATE:{end_date}
SUMMARY:{summary}
DESCRIPTION:{description}
PRIORITY:{1 if task.priority == 'High' else 5 if task.priority == 'Medium' else 9}
STATUS:{'COMPLETED' if task.status == 'Done' else 'IN-PROCESS' if task.status == 'In Progress' else 'NEEDS-ACTION'}
END:VEVENT
END:VCALENDAR"""
    
    # Create response with ICS file
    response = Response(
        ics_content,
        mimetype='text/calendar',
        headers={
            'Content-Disposition': f'attachment; filename=task-{task.id}-{task.title[:30].replace(" ", "-")}.ics'
        }
    )
    
    return response
