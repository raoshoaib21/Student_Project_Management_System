from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Project, ProjectMember
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
