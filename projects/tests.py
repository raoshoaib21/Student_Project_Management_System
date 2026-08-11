from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectMember, Task
from .permissions import is_project_leader, is_project_manager, is_project_member, scoped_projects

User = get_user_model()


class PermissionHelperTests(TestCase):
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
        ProjectMember.objects.create(project=self.project, user=self.member)

    def test_manager_checks(self):
        self.assertTrue(is_project_manager(self.owner, self.project))
        self.assertTrue(is_project_manager(self.supervisor, self.project))
        self.assertFalse(is_project_manager(self.member, self.project))

    def test_member_checks(self):
        self.assertTrue(is_project_member(self.member, self.project))
        self.assertTrue(is_project_member(self.owner, self.project))
        self.assertFalse(is_project_member(self.outsider, self.project))

    def test_leader_check(self):
        self.assertFalse(is_project_leader(self.member, self.project))
        leader = User.objects.create_user(username="leader", email="leader@example.com", password="x")
        leader.role = User.Role.STUDENT
        leader.save()
        ProjectMember.objects.create(project=self.project, user=leader, role=ProjectMember.Role.LEADER)
        self.assertTrue(is_project_leader(leader, self.project))

    def test_scoping(self):
        self.assertIn(self.project, list(scoped_projects(self.owner)))
        self.assertIn(self.project, list(scoped_projects(self.member)))
        self.assertIn(self.project, list(scoped_projects(self.supervisor)))
        self.assertNotIn(self.project, list(scoped_projects(self.outsider)))
        self.assertEqual(list(scoped_projects(self.outsider)), [])


class ProjectViewTests(TestCase):
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

    def test_list_requires_login(self):
        response = self.client.get(reverse("projects:project_list"))
        self.assertEqual(response.status_code, 302)

    def test_list_scoped(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("projects:project_list"))
        self.assertEqual(response.context["projects"].count(), 1)
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:project_list"))
        self.assertEqual(response.context["projects"].count(), 0)

    def test_create_project_sets_owner_and_leader(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("projects:project_create"),
            {"title": "New", "supervisor": self.supervisor.pk},
        )
        project = Project.objects.get(title="New")
        self.assertEqual(project.owner, self.outsider)
        self.assertTrue(ProjectMember.objects.filter(project=project, user=self.outsider, role=ProjectMember.Role.LEADER).exists())
        self.assertRedirects(response, project.get_absolute_url())

    def test_detail_denied_to_non_member(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_detail_allowed_for_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)

    def test_update_denied_to_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("projects:project_update", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_update_allowed_to_manager(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("projects:project_update", args=[self.project.pk]),
            {"title": "Renamed", "supervisor": self.supervisor.pk},
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Renamed")
        self.assertRedirects(response, self.project.get_absolute_url())

    def test_add_and_remove_member(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("projects:project_members", args=[self.project.pk]),
            {"user": self.outsider.pk, "role": ProjectMember.Role.MEMBER},
        )
        self.assertTrue(ProjectMember.objects.filter(project=self.project, user=self.outsider).exists())
        self.assertRedirects(response, reverse("projects:project_members", args=[self.project.pk]))
        member = ProjectMember.objects.get(project=self.project, user=self.outsider)
        self.client.post(
            reverse("projects:project_members", args=[self.project.pk]),
            {"remove_member_id": member.pk},
        )
        self.assertFalse(ProjectMember.objects.filter(pk=member.pk).exists())

    def test_members_denied_to_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("projects:project_members", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_delete_project(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("projects:project_delete", args=[self.project.pk]))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertRedirects(response, reverse("projects:project_list"))


class TaskViewTests(TestCase):
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
        self.task = Task.objects.create(
            project=self.project, title="T", assignee=self.member, created_by=self.owner
        )

    def test_task_create_allowed_for_member(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("projects:task_create", args=[self.project.pk]),
            {"title": "New task", "assignee": self.member.pk, "priority": Task.Priority.HIGH},
        )
        self.assertTrue(Task.objects.filter(project=self.project, title="New task").exists())
        self.assertRedirects(response, reverse("projects:project_detail", args=[self.project.pk]))

    def test_task_create_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("projects:task_create", args=[self.project.pk]),
            {"title": "New task", "assignee": self.member.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_task_edit_allowed_for_manager(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("projects:task_update", args=[self.task.pk]),
            {"title": "Edited", "assignee": self.member.pk, "priority": Task.Priority.MEDIUM, "status": Task.Status.IN_PROGRESS},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Edited")
        self.assertRedirects(response, reverse("projects:project_detail", args=[self.project.pk]))

    def test_task_edit_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:task_update", args=[self.task.pk]))
        self.assertEqual(response.status_code, 403)

    def test_task_delete(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("projects:task_delete", args=[self.task.pk]))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
        self.assertRedirects(response, reverse("projects:project_detail", args=[self.project.pk]))

    def test_status_change_by_member(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("projects:task_status", args=[self.task.pk]), {"status": Task.Status.DONE}
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)
        self.assertRedirects(response, reverse("projects:project_detail", args=[self.project.pk]))

    def test_task_list_assigned_to_me(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("projects:task_list"), {"assigned": "me"})
        self.assertIn(self.task, list(response.context["tasks"]))
        self.client.force_login(self.owner)
        response = self.client.get(reverse("projects:task_list"), {"assigned": "me"})
        self.assertNotIn(self.task, list(response.context["tasks"]))
