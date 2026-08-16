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


class PublicSiteTests(TestCase):
    def test_about_public(self):
        response = self.client.get(reverse("core:about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About")

    def test_contact_public(self):
        response = self.client.get(reverse("core:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Send a message")

    def test_contact_form_saves_message(self):
        from core.models import ContactMessage

        response = self.client.post(
            reverse("core:contact"),
            {"name": "Ayesha", "email": "ayesha@example.com", "subject": "Hello", "message": "Great platform!"},
        )
        self.assertRedirects(response, reverse("core:contact"))
        self.assertEqual(ContactMessage.objects.filter(email="ayesha@example.com").count(), 1)

    def test_contact_form_validation(self):
        response = self.client.post(
            reverse("core:contact"),
            {"name": "", "email": "not-an-email", "subject": "", "message": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")


class NotificationViewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", email="stu@example.com", password="x")
        self.student.role = User.Role.STUDENT
        self.student.save()
        Notification.objects.create(user=self.student, title="Unread one", url="/dashboard/")
        Notification.objects.create(user=self.student, title="Read one", is_read=True, url="/dashboard/")

    def test_list_requires_login(self):
        response = self.client.get(reverse("core:notification_list"))
        self.assertEqual(response.status_code, 302)

    def test_list_filters(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:notification_list"))
        self.assertEqual(response.context["notifications"].count(), 2)
        response = self.client.get(reverse("core:notification_list"), {"filter": "unread"})
        self.assertEqual(response.context["notifications"].count(), 1)
        response = self.client.get(reverse("core:notification_list"), {"filter": "read"})
        self.assertEqual(response.context["notifications"].count(), 1)

    def test_read_marks_and_redirects(self):
        self.client.force_login(self.student)
        notification = self.student.notifications.get(title="Unread one")
        response = self.client.get(reverse("core:notification_read", args=[notification.pk]))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertRedirects(response, notification.url)

    def test_read_ignores_other_users_notifications(self):
        other = User.objects.create_user(username="other", email="other@example.com", password="x")
        other.role = User.Role.STUDENT
        other.save()
        Notification.objects.create(user=other, title="Other's note", url="/dashboard/")
        self.client.force_login(self.student)
        other_notification = other.notifications.get()
        response = self.client.get(reverse("core:notification_read", args=[other_notification.pk]))
        self.assertEqual(response.status_code, 404)

    def test_read_all(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("core:notification_read_all"))
        self.assertEqual(self.student.notifications.filter(is_read=False).count(), 0)
        self.assertRedirects(response, reverse("core:notification_list"))

    def test_unauthenticated_read_all_rejected(self):
        response = self.client.post(reverse("core:notification_read_all"))
        self.assertEqual(response.status_code, 302)


class ActivityLogViewTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", email="stu@example.com", password="x")
        self.student.role = User.Role.STUDENT
        self.student.save()
        log_activity(self.student, "created project", "P1")
        log_activity(self.student, "updated task", "T1")

    def test_log_requires_login(self):
        response = self.client.get(reverse("core:activity_log"))
        self.assertEqual(response.status_code, 302)

    def test_log_lists_user_activity(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:activity_log"))
        self.assertEqual(response.context["activities"].count(), 2)

    def test_log_search(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("core:activity_log"), {"q": "created"})
        self.assertEqual(response.context["activities"].count(), 1)
