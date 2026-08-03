"""Seed the database with demo users, a project and tasks.

Usage: python manage.py seed_demo
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import StudentProfile, SupervisorProfile
from projects.models import Project, ProjectMember, Task

User = get_user_model()

SUPERVISOR_PASSWORD = "Supervisor2026!"
STUDENT_PASSWORD = "Student2026!"
ADMIN_PASSWORD = "Admin2026!"


class Command(BaseCommand):
    help = "Seed demo data: admin, supervisor, students, a project and tasks."

    def handle(self, *args, **options):
        self._get_or_create_admin()
        supervisor = self._get_or_create_supervisor()
        student1, student2 = self._get_or_create_students()
        project = self._create_project(supervisor, student1, student2)
        self._create_tasks(project, student1, student2)
        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    def _get_or_create_admin(self):
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "System",
                "last_name": "Admin",
                "role": User.Role.SUPERVISOR,
                "is_active": True,
                "is_email_verified": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.set_password(ADMIN_PASSWORD)
        user.is_active = True
        user.is_email_verified = True
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.stdout.write(f"Admin: admin / {ADMIN_PASSWORD}")
        return user

    def _get_or_create_supervisor(self):
        user, created = User.objects.get_or_create(
            username="demo_supervisor",
            defaults={
                "email": "demo_supervisor@example.com",
                "first_name": "Ayesha",
                "last_name": "Khan",
                "role": User.Role.SUPERVISOR,
                "is_active": True,
                "is_email_verified": True,
            },
        )
        user.set_password(SUPERVISOR_PASSWORD)
        user.is_active = True
        user.is_email_verified = True
        user.save()
        SupervisorProfile.objects.update_or_create(
            user=user,
            defaults={"title": "Senior Lecturer", "department": "Software Engineering"},
        )
        self.stdout.write(f"Supervisor: demo_supervisor / {SUPERVISOR_PASSWORD}")
        return user

    def _get_or_create_students(self):
        students = []
        for index, (username, first, last, reg) in enumerate(
            [
                ("demo_student1", "Ali", "Raza", "SPM-2026-101"),
                ("demo_student2", "Hina", "Noor", "SPM-2026-102"),
            ],
            start=1,
        ):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@student.example.com",
                    "first_name": first,
                    "last_name": last,
                    "role": User.Role.STUDENT,
                    "is_active": True,
                    "is_email_verified": True,
                },
            )
            user.set_password(STUDENT_PASSWORD)
            user.is_active = True
            user.is_email_verified = True
            user.save()
            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "registration_number": reg,
                    "department": "Software Engineering",
                    "course": "B.Sc. Computer Science",
                    "level": "500",
                },
            )
            self.stdout.write(f"Student: {username} / {STUDENT_PASSWORD}")
            students.append(user)
        return students

    def _create_project(self, supervisor, student1, student2):
        project, created = Project.objects.get_or_create(
            title="Final Year Project - Health Tracker",
            owner=student1,
            defaults={
                "supervisor": supervisor,
                "description": "A mobile-first web application to track daily health metrics.",
                "status": Project.Status.IN_PROGRESS,
                "start_date": timezone.localdate() - timezone.timedelta(days=30),
                "due_date": timezone.localdate() + timezone.timedelta(days=60),
            },
        )
        if created:
            ProjectMember.objects.get_or_create(project=project, user=student1, role=ProjectMember.Role.LEADER)
            ProjectMember.objects.get_or_create(project=project, user=student2, role=ProjectMember.Role.MEMBER)
            self.stdout.write(f"Project: {project.title}")
        return project

    def _create_tasks(self, project, student1, student2):
        tasks = [
            ("System requirements & scope", "Document functional and non-functional requirements.", student1, Task.Priority.HIGH, Task.Status.IN_PROGRESS),
            ("Database schema design", "Design the ERD and implement models/migrations.", student2, Task.Priority.URGENT, Task.Status.TODO),
            ("UI wireframes", "Create wireframes for all dashboard screens.", student1, Task.Priority.MEDIUM, Task.Status.TODO),
        ]
        for index, (title, description, assignee, priority, status) in enumerate(tasks):
            Task.objects.get_or_create(
                project=project,
                title=title,
                defaults={
                    "description": description,
                    "assignee": assignee,
                    "priority": priority,
                    "status": status,
                    "created_by": student1,
                    "due_date": timezone.localdate() + timezone.timedelta(days=14),
                },
            )
