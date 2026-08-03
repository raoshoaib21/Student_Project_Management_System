from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import StudentProfile, SupervisorProfile
from core.models import ActivityLog, Notification, log_activity
from documents.models import Document
from progress.models import Feedback, ProgressReport
from projects.models import Project, ProjectMember, Task

User = get_user_model()


class ModelSmokeTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(username="sup", email="sup@example.com", password="x")
        self.supervisor.role = User.Role.SUPERVISOR
        self.supervisor.save()
        SupervisorProfile.objects.create(user=self.supervisor, title="Senior Lecturer")

        self.student = User.objects.create_user(username="stu", email="stu@example.com", password="x")
        self.student.role = User.Role.STUDENT
        self.student.save()
        StudentProfile.objects.create(user=self.student, registration_number="R001")

    def test_permission_meta(self):
        codenames = {p[0] for p in Project._meta.permissions}
        self.assertIn("can_review_progress", codenames)

    def test_full_object_workflow(self):
        project = Project.objects.create(title="P1", owner=self.student, supervisor=self.supervisor)
        ProjectMember.objects.create(project=project, user=self.student, role=ProjectMember.Role.LEADER)
        task = Task.objects.create(project=project, title="T1", assignee=self.student, created_by=self.student)
        report = ProgressReport.objects.create(project=project, author=self.student, week_number=1, summary="Progress")
        Feedback.objects.create(progress_report=report, author=self.supervisor, content="Good work")
        Notification.objects.create(user=self.student, title="New feedback", url="/dashboard/")
        log_activity(self.student, "created project", project.title)

        self.assertEqual(project.member_count, 1)
        self.assertEqual(Task.objects.filter(project=project).count(), 1)
        self.assertEqual(ProgressReport.objects.filter(project=project).count(), 1)
        self.assertEqual(Feedback.objects.filter(progress_report=report).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.student).count(), 1)
        self.assertEqual(ActivityLog.objects.filter(user=self.student).count(), 1)

    def test_duplicate_weekly_report_rejected(self):
        project = Project.objects.create(title="P2", owner=self.student, supervisor=self.supervisor)
        ProgressReport.objects.create(project=project, author=self.student, week_number=1, summary="A")
        with self.assertRaises(Exception):
            ProgressReport.objects.create(project=project, author=self.student, week_number=1, summary="B")

    def test_document_save_populates_metadata(self):
        project = Project.objects.create(title="P3", owner=self.student, supervisor=self.supervisor)
        doc = Document.objects.create(
            project=project,
            uploaded_by=self.student,
            file=SimpleUploadedFile("notes.txt", b"hello world"),
        )
        self.assertEqual(doc.file_type, "txt")
        self.assertEqual(doc.size, 11)
        self.assertEqual(doc.name, "notes.txt")


class CoreViewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", email="stu@example.com", password="x")
        self.student.role = User.Role.STUDENT
        self.student.is_email_verified = True
        self.student.save()

    def test_landing_public(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_renders_for_student(self):
        self.client.post(reverse("accounts:login"), {"username": "stu", "password": "x"})
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
