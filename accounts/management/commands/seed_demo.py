"""Seed the database with a complete demo dataset.

Usage: python manage.py seed_demo
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import StudentProfile, SupervisorProfile
from core.models import Notification, log_activity
from documents.models import Document
from progress.models import Feedback, ProgressReport
from projects.models import Project, ProjectMember, Task

User = get_user_model()

SUPERVISOR_PASSWORD = "Supervisor2026!"
STUDENT_PASSWORD = "Student2026!"
ADMIN_PASSWORD = "Admin2026!"

TODAY = timezone.localdate()


class Command(BaseCommand):
    help = "Seed demo data: users, projects, tasks, documents, reports, notifications."

    def handle(self, *args, **options):
        self._get_or_create_admin()
        supervisor = self._get_or_create_supervisor()
        s1, s2, s3 = self._get_or_create_students()
        p1 = self._create_project1(supervisor, s1, s2, s3)
        p2 = self._create_project2(supervisor, s1, s2)
        self._create_tasks(p1, s1, s2, s3)
        self._create_tasks2(p2, s1, s2)
        self._create_documents(p1, s1, s2)
        self._create_documents(p2, s2, s1)
        self._create_reports(p1, s1, s2, supervisor)
        self._create_reports2(p2, s2, supervisor)
        self._create_notifications(s1, s2, supervisor)
        self.stdout.write(self.style.SUCCESS("Seed data created successfully."))

    # ── Users ────────────────────────────────────────────────────────

    def _get_or_create_admin(self):
        user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "System", "last_name": "Admin",
                "role": User.Role.SUPERVISOR, "is_staff": True, "is_superuser": True,
            },
        )
        user.set_password(ADMIN_PASSWORD)
        user.is_active = user.is_email_verified = user.is_staff = user.is_superuser = True
        user.save()
        self.stdout.write(f"Admin: admin / {ADMIN_PASSWORD}")
        return user

    def _get_or_create_supervisor(self):
        user, _ = User.objects.get_or_create(
            username="demo_supervisor",
            defaults={
                "email": "demo_supervisor@example.com",
                "first_name": "Ayesha", "last_name": "Khan",
                "role": User.Role.SUPERVISOR,
            },
        )
        user.set_password(SUPERVISOR_PASSWORD)
        user.is_active = user.is_email_verified = True
        user.save()
        SupervisorProfile.objects.update_or_create(
            user=user, defaults={"title": "Senior Lecturer", "department": "Software Engineering"},
        )
        self.stdout.write(f"Supervisor: demo_supervisor / {SUPERVISOR_PASSWORD}")
        return user

    def _get_or_create_students(self):
        students = []
        for username, first, last, reg in [
            ("demo_student1", "Ali", "Raza", "SPM-2026-101"),
            ("demo_student2", "Hina", "Noor", "SPM-2026-102"),
            ("demo_student3", "Omar", "Farooq", "SPM-2026-103"),
        ]:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@student.example.com",
                    "first_name": first, "last_name": last,
                    "role": User.Role.STUDENT,
                },
            )
            user.set_password(STUDENT_PASSWORD)
            user.is_active = user.is_email_verified = True
            user.save()
            StudentProfile.objects.update_or_create(
                user=user, defaults={
                    "registration_number": reg,
                    "department": "Software Engineering",
                    "course": "B.Sc. Computer Science", "level": "500",
                },
            )
            self.stdout.write(f"Student: {username} / {STUDENT_PASSWORD}")
            students.append(user)
        return students

    # ── Projects ─────────────────────────────────────────────────────

    def _create_project1(self, supervisor, s1, s2, s3):
        project, created = Project.objects.get_or_create(
            title="Health Tracker — Mobile Wellness App",
            owner=s1,
            defaults={
                "supervisor": supervisor,
                "description": "A mobile-first web application to track daily health metrics including steps, "
                               "sleep, water intake and calorie consumption, with weekly summaries and "
                               "supervisor-reviewed progress reports.",
                "status": Project.Status.IN_PROGRESS,
                "start_date": TODAY - timezone.timedelta(days=45),
                "due_date": TODAY + timezone.timedelta(days=50),
            },
        )
        if created:
            ProjectMember.objects.get_or_create(project=project, user=s1, role=ProjectMember.Role.LEADER)
            ProjectMember.objects.get_or_create(project=project, user=s2, role=ProjectMember.Role.MEMBER)
            ProjectMember.objects.get_or_create(project=project, user=s3, role=ProjectMember.Role.MEMBER)
            self.stdout.write(f"  Project 1: {project.title}")
        return project

    def _create_project2(self, supervisor, s1, s2):
        project, created = Project.objects.get_or_create(
            title="Campus Event Scheduler",
            owner=s2,
            defaults={
                "supervisor": supervisor,
                "description": "A scheduling platform for university clubs and departments to create, "
                               "promote and manage campus events with RSVP tracking and room booking.",
                "status": Project.Status.PLANNING,
                "start_date": TODAY - timezone.timedelta(days=10),
                "due_date": TODAY + timezone.timedelta(days=80),
            },
        )
        if created:
            ProjectMember.objects.get_or_create(project=project, user=s2, role=ProjectMember.Role.LEADER)
            ProjectMember.objects.get_or_create(project=project, user=s1, role=ProjectMember.Role.MEMBER)
            self.stdout.write(f"  Project 2: {project.title}")
        return project

    # ── Tasks ────────────────────────────────────────────────────────

    def _create_tasks(self, project, s1, s2, s3):
        tasks = [
            ("System requirements & scope", "Document functional and non-functional requirements for the health tracker.", s1, Task.Priority.HIGH, Task.Status.DONE),
            ("Database schema design", "Design the ERD and implement Django models with migrations.", s2, Task.Priority.HIGH, Task.Status.DONE),
            ("UI wireframes", "Create wireframes for all dashboard screens using Figma.", s1, Task.Priority.MEDIUM, Task.Status.IN_PROGRESS),
            ("User authentication module", "Implement registration, login, email verification and password reset.", s3, Task.Priority.HIGH, Task.Status.DONE),
            ("Health metrics API", "Build REST endpoints for step count, sleep, water and calorie tracking.", s2, Task.Priority.URGENT, Task.Status.IN_PROGRESS),
            ("Dashboard charts", "Implement Chart.js visualisations for weekly health trends.", s1, Task.Priority.MEDIUM, Task.Status.TODO),
            ("Data export feature", "Allow users to download health data as CSV.", s3, Task.Priority.LOW, Task.Status.TODO),
            ("Unit tests", "Write comprehensive tests for models, views and API endpoints.", s2, Task.Priority.HIGH, Task.Status.TODO),
            ("Deployment & documentation", "Deploy to Render and write the project README.", s1, Task.Priority.MEDIUM, Task.Status.TODO),
            ("Final presentation slides", "Prepare the final-year presentation deck.", s3, Task.Priority.MEDIUM, Task.Status.TODO),
        ]
        for title, desc, assignee, priority, status in tasks:
            Task.objects.get_or_create(
                project=project, title=title,
                defaults={
                    "description": desc, "assignee": assignee, "priority": priority,
                    "status": status, "created_by": project.owner,
                    "due_date": TODAY + timezone.timedelta(days=14),
                },
            )

    def _create_tasks2(self, project, s1, s2):
        tasks = [
            ("Requirements gathering", "Interview student clubs to understand scheduling needs.", s2, Task.Priority.HIGH, Task.Status.DONE),
            ("Competitor analysis", "Review existing event scheduling tools and identify gaps.", s1, Task.Priority.MEDIUM, Task.Status.IN_PROGRESS),
            ("UI/UX mockups", "Design the event creation and RSVP flows.", s2, Task.Priority.MEDIUM, Task.Status.TODO),
            ("Room booking integration", "Integrate with the university room booking system API.", s1, Task.Priority.HIGH, Task.Status.TODO),
            ("Push notifications", "Implement event reminders via browser push notifications.", s2, Task.Priority.LOW, Task.Status.TODO),
        ]
        for title, desc, assignee, priority, status in tasks:
            Task.objects.get_or_create(
                project=project, title=title,
                defaults={
                    "description": desc, "assignee": assignee, "priority": priority,
                    "status": status, "created_by": project.owner,
                    "due_date": TODAY + timezone.timedelta(days=30),
                },
            )

    # ── Documents ────────────────────────────────────────────────────

    def _create_documents(self, project, uploader1, uploader2):
        docs = [
            ("Project Proposal", "Final-year project proposal document.", uploader1, "pdf"),
            ("Requirements Specification", "Detailed functional and non-functional requirements.", uploader1, "pdf"),
            ("Database ERD", "Entity-Relationship diagram for the database schema.", uploader2, "png"),
            ("UI Wireframes v1", "Initial wireframe designs for all screens.", uploader1, "pdf"),
            ("Test Plan", "Comprehensive test plan covering unit, integration and UI tests.", uploader2, "txt"),
        ]
        for name, desc, uploaded_by, ext in docs:
            Document.objects.get_or_create(
                project=project, name=name,
                defaults={
                    "description": desc, "uploaded_by": uploaded_by,
                    "file": SimpleUploadedFile(f"{name.lower().replace(' ', '_')}.{ext}", f"Demo content for {name}".encode()),
                    "size": len(f"Demo content for {name}"),
                    "file_type": ext,
                },
            )

    # ── Progress Reports ─────────────────────────────────────────────

    def _create_reports(self, project, s1, s2, supervisor):
        reports = [
            (1, s1, ProgressReport.Status.APPROVED,
             "Set up the Django project and created initial models. User authentication is working.",
             "Project initialised, models created, auth working.", "Complete task assignment and status workflows."),
            (2, s1, ProgressReport.Status.APPROVED,
             "Implemented the health metrics API with full CRUD operations.",
             "API endpoints for steps, sleep, water and calories are live.", "Begin dashboard charts."),
            (3, s1, ProgressReport.Status.SUBMITTED,
             "Dashboard chart implementation started using Chart.js.",
             "Bar chart for weekly steps complete, line chart for sleep in progress.",
             "Finish all charts and start data export feature."),
            (4, s1, ProgressReport.Status.DRAFT,
             "Working on data export feature and finalising Chart.js visualisations.",
             "CSV export module scaffolded, 2 of 4 charts complete.", "Complete charts and write unit tests."),
        ]
        for week, author, status, summary, achievements, plan in reports:
            ProgressReport.objects.get_or_create(
                project=project, week_number=week, author=author,
                defaults={
                    "summary": summary, "achievements": achievements,
                    "next_week_plan": plan, "status": status,
                },
            )
        for week in [1, 2]:
            report = ProgressReport.objects.filter(project=project, week_number=week, author=s1).first()
            if report and not report.feedbacks.exists():
                Feedback.objects.create(
                    project=project, progress_report=report, author=supervisor,
                    content="Good progress this week. Keep up the momentum and stay on track with your plan.",
                )

    def _create_reports2(self, project, s2, supervisor):
        report, created = ProgressReport.objects.get_or_create(
            project=project, week_number=1, author=s2,
            defaults={
                "summary": "Completed the requirements gathering phase with interviews from 3 student clubs.",
                "achievements": "Identified key features: event creation, RSVP, room booking integration.",
                "next_week_plan": "Begin competitor analysis and start UI/UX mockups.",
                "status": ProgressReport.Status.APPROVED,
            },
        )
        if created:
            Feedback.objects.create(
                project=project, progress_report=report, author=supervisor,
                content="Thorough requirements analysis. Make sure to document user personas as well.",
            )

    # ── Notifications ────────────────────────────────────────────────

    def _create_notifications(self, s1, s2, supervisor):
        notifications = [
            (s1, "Welcome to Student PMS", "Your account is ready. Start by creating your first project.", "/dashboard/"),
            (s1, "New task assigned", "You have been assigned 'Dashboard charts' in Health Tracker.", "/projects/1/"),
            (s1, "Feedback received", "Ayesha Khan left feedback on your Week 1 report.", "/progress/1/"),
            (s2, "New task assigned", "You have been assigned 'Requirements gathering' in Campus Event Scheduler.", "/projects/2/"),
            (s2, "Report needs revision", "Your Week 2 report was sent back for revision.", "/progress/2/"),
            (supervisor, "Progress report submitted", "Ali Raza submitted Week 3 report for Health Tracker.", "/progress/3/"),
        ]
        for user, title, message, url in notifications:
            Notification.objects.get_or_create(
                user=user, title=title, defaults={"message": message, "url": url},
            )
