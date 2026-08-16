from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Notification
from projects.models import Project, ProjectMember

from .models import Document

User = get_user_model()


class DocumentViewTests(TestCase):
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
        self.document = Document.objects.create(
            project=self.project,
            uploaded_by=self.owner,
            file=SimpleUploadedFile("design.txt", b"design contents"),
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse("documents:document_list"))
        self.assertEqual(response.status_code, 302)

    def test_list_scoped_to_user(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("documents:document_list"))
        self.assertEqual(response.context["documents"].count(), 1)
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("documents:document_list"))
        self.assertEqual(response.context["documents"].count(), 0)

    def test_upload_notifies_project_members(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("documents:document_upload", args=[self.project.pk]),
            {"name": "Proposal.pdf", "file": SimpleUploadedFile("Proposal.pdf", b"pdf-bytes")},
        )
        doc = Document.objects.get(name="Proposal.pdf")
        self.assertRedirects(response, doc.get_absolute_url())
        recipients = set(Notification.objects.values_list("user_id", flat=True))
        self.assertIn(self.owner.id, recipients)
        self.assertIn(self.supervisor.id, recipients)
        self.assertNotIn(self.member.id, recipients)

    def test_upload_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("documents:document_upload", args=[self.project.pk]),
            {"name": "Proposal.pdf", "file": SimpleUploadedFile("Proposal.pdf", b"pdf-bytes")},
        )
        self.assertEqual(response.status_code, 403)

    def test_detail_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("documents:document_detail", args=[self.document.pk]))
        self.assertEqual(response.status_code, 403)

    def test_detail_allowed_for_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:document_detail", args=[self.document.pk]))
        self.assertEqual(response.status_code, 200)

    def test_update_denied_for_plain_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:document_update", args=[self.document.pk]))
        self.assertEqual(response.status_code, 403)

    def test_update_allowed_for_uploader(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("documents:document_update", args=[self.document.pk]),
            {"description": "Final design", "file": SimpleUploadedFile("design.txt", b"new contents")},
        )
        self.document.refresh_from_db()
        self.assertEqual(self.document.description, "Final design")
        self.assertRedirects(response, self.document.get_absolute_url())

    def test_update_description_without_new_file(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("documents:document_update", args=[self.document.pk]),
            {"description": "Description only"},
        )
        self.document.refresh_from_db()
        self.assertEqual(self.document.description, "Description only")
        self.assertEqual(self.document.name, "design.txt")
        self.assertRedirects(response, self.document.get_absolute_url())

    def test_delete_document(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("documents:document_delete", args=[self.document.pk]))
        self.assertFalse(Document.objects.filter(pk=self.document.pk).exists())
        self.assertRedirects(response, reverse("documents:document_list"))

    def test_download_allowed_for_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("documents:document_download", args=[self.document.pk]))
        self.assertEqual(response.status_code, 200)

    def test_download_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("documents:document_download", args=[self.document.pk]))
        self.assertEqual(response.status_code, 403)
