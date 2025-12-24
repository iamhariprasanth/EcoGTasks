"""
Database Seed Script
Creates demo users, projects, and tasks for testing.

Run with: python seed.py
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from app import create_app, db
from app.backend.models import User, Project, Task, Comment, TaskHistory, UserRole, TaskStatus, TaskPriority


def seed_database():
    """Seed the database with demo data."""
    print("🌱 Starting database seeding...")
    
    app = create_app('development')
    
    with app.app_context():
        # Check if data already exists
        if User.query.first():
            print("⚠️  Database already contains data. Skipping seed.")
            print("   To reseed, delete the database file and run again.")
            return
        
        # Create users
        print("👤 Creating users...")
        
        admin = User(
            username='admin',
            email='admin@company.com',
            role=UserRole.ADMIN.value,
            is_approved=True  # Admin approved by default
        )
        admin.set_password('admin123')
        
        manager1 = User(
            username='manager',
            email='manager@company.com',
            role=UserRole.MANAGER.value,
            is_approved=True
        )
        manager1.set_password('manager123')
        
        manager2 = User(
            username='sarah',
            email='sarah@company.com',
            role=UserRole.MANAGER.value,
            is_approved=True
        )
        manager2.set_password('sarah123')
        
        employee1 = User(
            username='employee',
            email='employee@company.com',
            role=UserRole.EMPLOYEE.value,
            is_approved=True
        )
        employee1.set_password('employee123')
        
        employee2 = User(
            username='john',
            email='john@company.com',
            role=UserRole.EMPLOYEE.value,
            is_approved=True
        )
        employee2.set_password('john123')
        
        employee3 = User(
            username='alice',
            email='alice@company.com',
            role=UserRole.EMPLOYEE.value,
            is_approved=True
        )
        employee3.set_password('alice123')
        
        employee4 = User(
            username='bob',
            email='bob@company.com',
            role=UserRole.EMPLOYEE.value,
            is_approved=True
        )
        employee4.set_password('bob123')
        
        all_users = [admin, manager1, manager2, employee1, employee2, employee3, employee4]
        db.session.add_all(all_users)
        db.session.commit()
        
        print(f"   ✅ Created {len(all_users)} users")
        
        # Create projects
        print("📁 Creating projects...")
        
        project1 = Project(
            name='Website Redesign',
            description='Complete overhaul of the company website with modern UI/UX.',
            created_by=manager1.id
        )
        
        project2 = Project(
            name='Mobile App Development',
            description='Native mobile application for iOS and Android platforms.',
            created_by=manager2.id
        )
        
        project3 = Project(
            name='API Integration',
            description='Integration of third-party APIs for payment and authentication.',
            created_by=manager1.id
        )
        
        projects = [project1, project2, project3]
        db.session.add_all(projects)
        db.session.commit()
        
        # Add members to projects
        project1.members.extend([manager1, employee1, employee2, employee3])
        project2.members.extend([manager2, employee3, employee4])
        project3.members.extend([manager1, employee2, employee4])
        db.session.commit()
        
        print(f"   ✅ Created {len(projects)} projects")
        
        # Create tasks
        print("📋 Creating tasks...")
        
        tasks_data = [
            # Website Redesign tasks
            {
                'title': 'Design new homepage mockup',
                'description': 'Create wireframes and high-fidelity mockups for the new homepage design.',
                'status': TaskStatus.DONE.value,
                'priority': TaskPriority.HIGH.value,
                'project_id': project1.id,
                'assigned_to': employee1.id,
                'created_by': manager1.id,
                'due_date': date.today() - timedelta(days=5)
            },
            {
                'title': 'Implement responsive navigation',
                'description': 'Build mobile-first responsive navigation component.',
                'status': TaskStatus.IN_PROGRESS.value,
                'priority': TaskPriority.HIGH.value,
                'project_id': project1.id,
                'assigned_to': employee2.id,
                'created_by': manager1.id,
                'due_date': date.today() + timedelta(days=3)
            },
            {
                'title': 'Set up new CMS',
                'description': 'Install and configure headless CMS for content management.',
                'status': TaskStatus.TODO.value,
                'priority': TaskPriority.MEDIUM.value,
                'project_id': project1.id,
                'assigned_to': employee1.id,
                'created_by': manager1.id,
                'due_date': date.today() + timedelta(days=7)
            },
            {
                'title': 'Optimize images and assets',
                'description': 'Compress images and optimize loading performance.',
                'status': TaskStatus.TODO.value,
                'priority': TaskPriority.LOW.value,
                'project_id': project1.id,
                'assigned_to': None,
                'created_by': manager1.id,
                'due_date': date.today() + timedelta(days=14)
            },
            
            # Mobile App tasks
            {
                'title': 'Set up React Native project',
                'description': 'Initialize React Native project with TypeScript configuration.',
                'status': TaskStatus.DONE.value,
                'priority': TaskPriority.HIGH.value,
                'project_id': project2.id,
                'assigned_to': employee3.id,
                'created_by': manager2.id,
                'due_date': date.today() - timedelta(days=10)
            },
            {
                'title': 'Design app authentication flow',
                'description': 'Create login, registration, and password reset screens.',
                'status': TaskStatus.DONE.value,
                'priority': TaskPriority.HIGH.value,
                'project_id': project2.id,
                'assigned_to': employee4.id,
                'created_by': manager2.id,
                'due_date': date.today() - timedelta(days=3)
            },
            {
                'title': 'Implement push notifications',
                'description': 'Set up Firebase Cloud Messaging for push notifications.',
                'status': TaskStatus.IN_PROGRESS.value,
                'priority': TaskPriority.MEDIUM.value,
                'project_id': project2.id,
                'assigned_to': employee3.id,
                'created_by': manager2.id,
                'due_date': date.today() + timedelta(days=5)
            },
            {
                'title': 'Build user profile screen',
                'description': 'Create editable user profile with avatar upload.',
                'status': TaskStatus.TODO.value,
                'priority': TaskPriority.MEDIUM.value,
                'project_id': project2.id,
                'assigned_to': employee4.id,
                'created_by': manager2.id,
                'due_date': date.today() + timedelta(days=8)
            },
            
            # API Integration tasks
            {
                'title': 'Integrate Stripe payment API',
                'description': 'Set up Stripe SDK and implement payment processing.',
                'status': TaskStatus.IN_PROGRESS.value,
                'priority': TaskPriority.HIGH.value,
                'project_id': project3.id,
                'assigned_to': employee2.id,
                'created_by': manager1.id,
                'due_date': date.today() + timedelta(days=2)
            },
            {
                'title': 'Add OAuth2 authentication',
                'description': 'Implement Google and GitHub OAuth login.',
                'status': TaskStatus.TODO.value,
                'priority': TaskPriority.HIGH.value,
                'project_id': project3.id,
                'assigned_to': employee4.id,
                'created_by': manager1.id,
                'due_date': date.today() + timedelta(days=6)
            },
            {
                'title': 'Create API documentation',
                'description': 'Document all API endpoints using OpenAPI/Swagger.',
                'status': TaskStatus.TODO.value,
                'priority': TaskPriority.LOW.value,
                'project_id': project3.id,
                'assigned_to': None,
                'created_by': manager1.id,
                'due_date': date.today() + timedelta(days=20)
            },
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            task = Task(**task_data)
            db.session.add(task)
            created_tasks.append(task)
        
        db.session.commit()
        print(f"   ✅ Created {len(created_tasks)} tasks")
        
        # Add some comments
        print("💬 Creating comments...")
        
        comments_data = [
            {'task': created_tasks[1], 'user': employee2, 'content': 'Started working on the mobile menu. Should have a draft ready by tomorrow.'},
            {'task': created_tasks[1], 'user': manager1, 'content': 'Great! Let me know if you need any design assets.'},
            {'task': created_tasks[4], 'user': employee3, 'content': 'Project setup complete. All dependencies installed successfully.'},
            {'task': created_tasks[6], 'user': employee3, 'content': 'FCM token registration is working. Testing on both platforms now.'},
            {'task': created_tasks[8], 'user': employee2, 'content': 'Stripe test mode is working. Need production keys for final testing.'},
        ]
        
        for comment_data in comments_data:
            comment = Comment(
                task_id=comment_data['task'].id,
                user_id=comment_data['user'].id,
                content=comment_data['content']
            )
            db.session.add(comment)
        
        db.session.commit()
        print(f"   ✅ Created {len(comments_data)} comments")
        
        # Add task history
        print("📜 Creating task history...")
        
        for task in created_tasks:
            history = TaskHistory(
                task_id=task.id,
                user_id=task.created_by,
                action='created'
            )
            db.session.add(history)
        
        # Add some status changes
        history_entries = [
            TaskHistory(task_id=created_tasks[0].id, user_id=employee1.id, action='status_changed', field_name='status', old_value='To Do', new_value='Done'),
            TaskHistory(task_id=created_tasks[1].id, user_id=employee2.id, action='status_changed', field_name='status', old_value='To Do', new_value='In Progress'),
            TaskHistory(task_id=created_tasks[4].id, user_id=employee3.id, action='status_changed', field_name='status', old_value='In Progress', new_value='Done'),
        ]
        db.session.add_all(history_entries)
        db.session.commit()
        
        print("   ✅ Created task history entries")
        
        print("\n" + "="*50)
        print("✅ Database seeding completed successfully!")
        print("="*50)
        print("\n📋 Demo Credentials:")
        print("-"*50)
        print("Admin:    admin@company.com    / admin123")
        print("Manager:  manager@company.com  / manager123")
        print("Manager:  sarah@company.com    / sarah123")
        print("Employee: employee@company.com / employee123")
        print("Employee: john@company.com     / john123")
        print("Employee: alice@company.com    / alice123")
        print("Employee: bob@company.com      / bob123")
        print("-"*50)
        print("\n🚀 Start the server with: python run.py")
        print("   Then visit: http://127.0.0.1:5000")


if __name__ == '__main__':
    seed_database()
