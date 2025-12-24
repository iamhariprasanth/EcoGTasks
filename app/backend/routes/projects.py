"""
Project Routes
Project management with member assignment.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from app.backend.models import Project, User, Task, TaskStatus
from app.backend.utils.forms import ProjectForm, ProjectMemberForm
from app.backend.utils.decorators import manager_required, project_access_required

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
@login_required
def list_projects():
    """
    List all projects accessible to the user.
    Admins see all projects, others see their assigned projects.
    """
    if current_user.is_admin():
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
    else:
        # Get projects user is a member of or has created
        member_projects = current_user.projects
        created_projects = list(current_user.created_projects.filter_by(is_active=True))
        projects = list(set(member_projects + created_projects))
        projects.sort(key=lambda p: p.name)
    
    # Add task counts for each project
    project_data = []
    for project in projects:
        total_tasks = project.tasks.count()
        done_tasks = project.tasks.filter_by(status=TaskStatus.DONE.value).count()
        project_data.append({
            'project': project,
            'total_tasks': total_tasks,
            'done_tasks': done_tasks,
            'member_count': project.members.count()
        })
    
    return render_template('projects/list.html', title='Projects', project_data=project_data)


@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
@manager_required
def create_project():
    """
    Create a new project (Manager/Admin only).
    """
    form = ProjectForm()
    
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data,
            created_by=current_user.id
        )
        
        db.session.add(project)
        db.session.commit()
        
        # Add creator as a member
        project.members.append(current_user)
        db.session.commit()
        
        flash(f'Project "{project.name}" created successfully!', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/form.html', form=form, title='Create Project', is_edit=False)


@projects_bp.route('/<int:project_id>')
@login_required
@project_access_required
def view_project(project_id):
    """
    View project details with tasks and members.
    """
    project = Project.query.get_or_404(project_id)
    member_form = ProjectMemberForm()
    
    # Get available users to add as members
    current_member_ids = [m.id for m in project.members]
    available_users = User.query.filter(
        User.is_active == True,
        ~User.id.in_(current_member_ids) if current_member_ids else True
    ).order_by(User.username).all()
    
    member_form.user_id.choices = [(u.id, f'{u.username} ({u.email})') for u in available_users]
    
    # Get project tasks with pagination
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    tasks_query = project.tasks
    if status_filter:
        tasks_query = tasks_query.filter_by(status=status_filter)
    
    pagination = tasks_query.order_by(Task.updated_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    tasks = pagination.items
    
    # Task statistics
    total_tasks = project.tasks.count()
    todo_count = project.tasks.filter_by(status=TaskStatus.TODO.value).count()
    in_progress_count = project.tasks.filter_by(status=TaskStatus.IN_PROGRESS.value).count()
    done_count = project.tasks.filter_by(status=TaskStatus.DONE.value).count()
    
    return render_template(
        'projects/detail.html',
        title=project.name,
        project=project,
        tasks=tasks,
        pagination=pagination,
        member_form=member_form,
        available_users=available_users,
        total_tasks=total_tasks,
        todo_count=todo_count,
        in_progress_count=in_progress_count,
        done_count=done_count,
        status_filter=status_filter
    )


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@project_access_required
def edit_project(project_id):
    """
    Edit project details (Manager/Admin or project owner).
    """
    project = Project.query.get_or_404(project_id)
    
    # Check permission
    if not (current_user.is_admin() or current_user.is_manager() or project.created_by == current_user.id):
        flash('You do not have permission to edit this project.', 'danger')
        abort(403)
    
    form = ProjectForm(obj=project)
    
    if form.validate_on_submit():
        project.name = form.name.data
        project.description = form.description.data
        db.session.commit()
        
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects.view_project', project_id=project.id))
    
    return render_template('projects/form.html', form=form, title='Edit Project', is_edit=True, project=project)


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@project_access_required
def delete_project(project_id):
    """
    Delete a project (Admin only).
    """
    if not current_user.is_admin():
        flash('Only administrators can delete projects.', 'danger')
        abort(403)
    
    project = Project.query.get_or_404(project_id)
    project_name = project.name
    
    db.session.delete(project)
    db.session.commit()
    
    flash(f'Project "{project_name}" has been deleted.', 'success')
    return redirect(url_for('projects.list_projects'))


@projects_bp.route('/<int:project_id>/members/add', methods=['POST'])
@login_required
@project_access_required
def add_member(project_id):
    """
    Add a member to the project (Manager/Admin).
    """
    project = Project.query.get_or_404(project_id)
    
    # Check permission
    if not (current_user.is_admin() or current_user.is_manager() or project.created_by == current_user.id):
        flash('You do not have permission to manage project members.', 'danger')
        abort(403)
    
    form = ProjectMemberForm()
    available_users = User.query.filter_by(is_active=True).all()
    form.user_id.choices = [(u.id, u.username) for u in available_users]
    
    if form.validate_on_submit():
        user = User.query.get(form.user_id.data)
        if user and user not in project.members.all():
            project.members.append(user)
            db.session.commit()
            flash(f'{user.username} has been added to the project.', 'success')
        else:
            flash('User is already a member of this project.', 'warning')
    
    return redirect(url_for('projects.view_project', project_id=project_id))


@projects_bp.route('/<int:project_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
@project_access_required
def remove_member(project_id, user_id):
    """
    Remove a member from the project (Manager/Admin).
    """
    project = Project.query.get_or_404(project_id)
    
    # Check permission
    if not (current_user.is_admin() or current_user.is_manager() or project.created_by == current_user.id):
        flash('You do not have permission to manage project members.', 'danger')
        abort(403)
    
    user = User.query.get_or_404(user_id)
    
    # Prevent removing the project owner
    if user.id == project.created_by:
        flash('Cannot remove the project owner.', 'danger')
        return redirect(url_for('projects.view_project', project_id=project_id))
    
    if user in project.members.all():
        project.members.remove(user)
        db.session.commit()
        flash(f'{user.username} has been removed from the project.', 'success')
    else:
        flash('User is not a member of this project.', 'warning')
    
    return redirect(url_for('projects.view_project', project_id=project_id))
