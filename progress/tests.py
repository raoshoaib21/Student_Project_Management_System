from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Notification
from projects.models import Project, ProjectMember

from .models import Feedback, ProgressReport

User = get_user_model()


class ProgressReportViewTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(username="sup", email="sup@example.com", password="x")
        self.supervisor.role = User.Role.SUPERVISOR
        self.supervisor.save()
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", password="x")
        self.owner.role = User.Role.STUDENT
        self.owner.save()
        self.member = User.objects.create_user(username="member", email="member@example.com", password="x")
        self.member.role = User.Role.STUDENT
        self.member.save()
        self.outsider = User.objects.create_user(username="outsider", email="outsider@example.com", password="x")
        self.outsider.role = User.Role.STUDENT
        self.outsider.save()
        self.project = Project.objects.create(title="P", owner=self.owner, supervisor=self.supervisor)
        ProjectMember.objects.create(project=self.project, user=self.owner, role=ProjectMember.Role.LEADER)
        ProjectMember.objects.create(project=self.project, user=self.member)
        self.report = ProgressReport.objects.create(
            project=self.project, author=self.member, week_number=1, summary="Progress this week"
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("progress:report_list"))
        self.assertEqual(response.status_code, 302)

    def test_list_scoped_to_user(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("progress:report_list"))
        self.assertEqual(response.context["reports"].count(), 1)
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("progress:report_list"))
        self.assertEqual(response.context["reports"].count(), 0)

    def test_create_report(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("progress:report_create", args=[self.project.pk]),
            {"week_number": 2, "summary": "Second week"},
        )
        report = ProgressReport.objects.get(week_number=2, project=self.project)
        self.assertEqual(report.author, self.member)
        self.assertRedirects(response, report.get_absolute_url())

    def test_create_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("progress:report_create", args=[self.project.pk]),
            {"week_number": 2, "summary": "Second week"},
        )
        self.assertEqual(response.status_code, 403)

    def test_detail_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("progress:report_detail", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)

    def test_detail_allowed_for_manager(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("progress:report_detail", args=[self.report.pk]))
        self.assertEqual(response.status_code, 200)

    def test_submit_moves_to_submitted_and_notifies_supervisor(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("progress:report_submit", args=[self.report.pk]))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, ProgressReport.Status.SUBMITTED)
        self.assertRedirects(response, self.report.get_absolute_url())
        self.assertTrue(
            Notification.objects.filter(
                user=self.supervisor, title="Progress report submitted"
            ).exists()
        )

    def test_review_approve_by_supervisor(self):
        self.report.status = ProgressReport.Status.SUBMITTED
        self.report.save()
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("progress:report_review", args=[self.report.pk]), {"action": "approve"}
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, ProgressReport.Status.APPROVED)
        self.assertRedirects(response, self.report.get_absolute_url())
        self.assertTrue(
            Notification.objects.filter(user=self.member, title__startswith="Report").exists()
        )

    def test_review_revision_requested(self):
        self.report.status = ProgressReport.Status.SUBMITTED
        self.report.save()
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("progress:report_review", args=[self.report.pk]), {"action": "revision"}
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, ProgressReport.Status.NEEDS_REVISION)

    def test_review_denied_for_author(self):
        self.report.status = ProgressReport.Status.SUBMITTED
        self.report.save()
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("progress:report_review", args=[self.report.pk]), {"action": "approve"}
        )
        self.assertEqual(response.status_code, 403)

    def test_feedback_posted_by_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("progress:report_detail", args=[self.report.pk]), {"content": "Great work"}
        )
        self.assertTrue(
            Feedback.objects.filter(progress_report=self.report, author=self.supervisor).exists()
        )
        self.assertRedirects(response, self.report.get_absolute_url())

    def test_feedback_denied_for_student(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("progress:report_detail", args=[self.report.pk]), {"content": "Great work"}
        )
        self.assertEqual(response.status_code, 403)

    def test_update_allowed_for_author(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("progress:report_update", args=[self.report.pk]),
            {"week_number": 1, "summary": "Updated summary"},
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.summary, "Updated summary")
        self.assertRedirects(response, self.report.get_absolute_url())

    def test_update_denied_for_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("progress:report_update", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)

    def test_update_denied_for_manager(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("progress:report_update", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)

    def test_update_denied_for_other_student(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("progress:report_update", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)

    def test_submit_denied_for_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(reverse("progress:report_submit", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, ProgressReport.Status.DRAFT)

    def test_delete_denied_for_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(reverse("progress:report_delete", args=[self.report.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ProgressReport.objects.filter(pk=self.report.pk).exists())

    def test_duplicate_week_rejected_by_form(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("progress:report_create", args=[self.project.pk]),
            {"week_number": 1, "summary": "Duplicate"},
        )
        self.assertEqual(ProgressReport.objects.filter(project=self.project, week_number=1).count(), 1)
        self.assertContains(response, "already exists")

    def test_delete_report(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("progress:report_delete", args=[self.report.pk]))
        self.assertFalse(ProgressReport.objects.filter(pk=self.report.pk).exists())
        self.assertRedirects(response, reverse("progress:report_list"))
