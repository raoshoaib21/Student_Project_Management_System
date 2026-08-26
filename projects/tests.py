from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectMember, ProjectProposal, Task
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

    def test_create_denied_to_student(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("projects:project_create"),
            {"title": "New", "supervisor": self.supervisor.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Project.objects.filter(title="New").exists())

    def test_create_allowed_for_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:project_create"),
            {"title": "Assigned", "supervisor": self.supervisor.pk},
        )
        project = Project.objects.get(title="Assigned")
        self.assertEqual(project.owner, self.supervisor)
        self.assertRedirects(response, project.get_absolute_url())

    def test_detail_denied_to_non_member(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_detail_allowed_for_member(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task Updates")
        self.assertContains(response, "Project Submission")
        self.assertContains(response, "Submit Final Document")
        self.assertNotContains(response, "Share Resource")
        self.assertNotContains(response, "New Task")

    def test_detail_shows_management_to_supervisor_only(self):
        # Student owner must NOT see task management even though they own the project.
        self.client.force_login(self.owner)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertContains(response, "Submit Final Document")
        self.assertNotContains(response, "New Task")
        self.assertNotContains(response, 'title="Edit"')
        self.assertNotContains(response, 'title="Delete"')
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertContains(response, "Share Resource")
        self.assertContains(response, "New Task")

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


class ProjectDecisionTests(TestCase):
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
        self.other_supervisor = User.objects.create_user(username="sup2", email="sup2@example.com", password="x")
        self.other_supervisor.role = User.Role.SUPERVISOR
        self.other_supervisor.save()
        self.project = Project.objects.create(title="P", owner=self.owner, supervisor=self.supervisor)
        ProjectMember.objects.create(project=self.project, user=self.owner, role=ProjectMember.Role.LEADER)
        ProjectMember.objects.create(project=self.project, user=self.member)

    def test_approve_by_assigned_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:project_decide", args=[self.project.pk]),
            {"decision": "approve", "decision_note": "Meets all requirements."},
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.approval_status, Project.ApprovalStatus.APPROVED)
        self.assertEqual(self.project.decision_note, "Meets all requirements.")
        self.assertEqual(self.project.decided_by, self.supervisor)
        self.assertIsNotNone(self.project.decided_at)
        self.assertRedirects(response, self.project.get_absolute_url())

    def test_decline_by_assigned_supervisor(self):
        self.client.force_login(self.supervisor)
        self.client.post(
            reverse("projects:project_decide", args=[self.project.pk]),
            {"decision": "decline", "decision_note": "Scope too narrow."},
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.approval_status, Project.ApprovalStatus.DECLINED)

    def test_decide_denied_to_students_and_other_supervisors(self):
        for user in (self.owner, self.member, self.other_supervisor):
            self.client.force_login(user)
            response = self.client.post(
                reverse("projects:project_decide", args=[self.project.pk]),
                {"decision": "approve"},
            )
            self.assertEqual(response.status_code, 403, f"{user} should be denied")
        self.project.refresh_from_db()
        self.assertEqual(self.project.approval_status, Project.ApprovalStatus.PENDING)

    def test_decision_requires_valid_choice(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:project_decide", args=[self.project.pk]),
            {"decision": "maybe"},
        )
        self.assertRedirects(response, self.project.get_absolute_url())
        self.project.refresh_from_db()
        self.assertEqual(self.project.approval_status, Project.ApprovalStatus.PENDING)

    def test_decision_notifies_members(self):
        from core.models import Notification

        before = Notification.objects.count()
        self.client.force_login(self.supervisor)
        self.client.post(
            reverse("projects:project_decide", args=[self.project.pk]),
            {"decision": "approve"},
        )
        self.assertEqual(Notification.objects.count(), before + 2)  # owner + member


class ProjectGradeTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(username="sup", email="sup@example.com", password="x")
        self.supervisor.role = User.Role.SUPERVISOR
        self.supervisor.save()
        self.student = User.objects.create_user(username="owner", email="owner@example.com", password="x")
        self.student.role = User.Role.STUDENT
        self.student.save()
        self.outsider = User.objects.create_user(username="outsider", email="o@example.com", password="x")
        self.outsider.role = User.Role.STUDENT
        self.outsider.save()
        self.project = Project.objects.create(title="P", owner=self.student, supervisor=self.supervisor)
        ProjectMember.objects.create(project=self.project, user=self.student, role=ProjectMember.Role.LEADER)

    def test_grade_by_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:project_grade", args=[self.project.pk]),
            {"grade": Project.Grade.A_PLUS, "grade_comment": "Excellent work."},
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.grade, "A+")
        self.assertEqual(self.project.graded_by, self.supervisor)
        self.assertIsNotNone(self.project.graded_at)
        self.assertRedirects(response, self.project.get_absolute_url())

    def test_grade_denied_to_others(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("projects:project_grade", args=[self.project.pk]),
            {"grade": Project.Grade.A},
        )
        self.assertEqual(response.status_code, 403)
        self.project.refresh_from_db()
        self.assertEqual(self.project.grade, "")

    def test_grade_visible_to_student_on_detail(self):
        from django.utils import timezone

        self.project.grade = Project.Grade.B_PLUS
        self.project.grade_comment = "Good effort."
        self.project.graded_by = self.supervisor
        self.project.graded_at = timezone.now()
        self.project.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertContains(response, "B+")
        self.assertContains(response, "Good effort.")

    def test_grade_required(self):
        self.client.force_login(self.supervisor)
        self.client.post(
            reverse("projects:project_grade", args=[self.project.pk]),
            {"grade": "", "grade_comment": "no grade"},
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.grade, "")


class ProposalFlowTests(TestCase):
    def setUp(self):
        self.supervisor = User.objects.create_user(username="sup", email="sup@example.com", password="x")
        self.supervisor.role = User.Role.SUPERVISOR
        self.supervisor.save()
        self.other_supervisor = User.objects.create_user(username="sup2", email="sup2@example.com", password="x")
        self.other_supervisor.role = User.Role.SUPERVISOR
        self.other_supervisor.save()
        self.student = User.objects.create_user(username="student", email="student@example.com", password="x")
        self.student.role = User.Role.STUDENT
        self.student.save()
        self.proposal = ProjectProposal.objects.create(
            student=self.student,
            supervisor=self.supervisor,
            title="Campus Navigator",
            description="A map app for campus navigation.",
        )

    def test_student_creates_proposal_notifies_selected_supervisor(self):
        from core.models import Notification

        before = Notification.objects.count()
        self.client.force_login(self.student)
        response = self.client.post(
            reverse("projects:proposal_create"),
            {
                "supervisor": self.supervisor.pk,
                "title": "Study Buddy",
                "description": "Match students for group study.",
            },
        )
        proposal = ProjectProposal.objects.get(title="Study Buddy")
        self.assertEqual(proposal.student, self.student)
        self.assertEqual(proposal.supervisor, self.supervisor)
        self.assertEqual(proposal.status, ProjectProposal.Status.PENDING)
        self.assertRedirects(response, reverse("projects:proposal_list"))
        latest = Notification.objects.order_by("-pk").first()
        self.assertEqual(Notification.objects.count(), before + 1)
        self.assertEqual(latest.user, self.supervisor)

    def test_supervisor_cannot_propose(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("projects:proposal_create"))
        self.assertEqual(response.status_code, 403)

    def test_approve_creates_assigned_project(self):
        from core.models import Notification

        before = Notification.objects.count()
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:proposal_decide", args=[self.proposal.pk]),
            {"decision": "approve", "decision_note": "Solid idea."},
        )
        self.assertRedirects(response, reverse("projects:proposal_list"))
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProjectProposal.Status.APPROVED)
        project = self.proposal.project
        self.assertIsNotNone(project)
        self.assertEqual(project.owner, self.supervisor)
        self.assertEqual(project.supervisor, self.supervisor)
        self.assertTrue(
            ProjectMember.objects.filter(project=project, user=self.student, role=ProjectMember.Role.LEADER).exists()
        )
        self.assertEqual(Notification.objects.count(), before + 1)

    def test_decline_stores_feedback_and_notifies(self):
        from core.models import Notification

        before = Notification.objects.count()
        self.client.force_login(self.supervisor)
        self.client.post(
            reverse("projects:proposal_decide", args=[self.proposal.pk]),
            {"decision": "decline", "decision_note": "Narrow the scope to one building."},
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProjectProposal.Status.DECLINED)
        self.assertEqual(self.proposal.supervisor_feedback, "Narrow the scope to one building.")
        self.assertIsNone(self.proposal.project)
        self.assertFalse(Project.objects.filter(title="Campus Navigator").exists())
        self.assertEqual(Notification.objects.count(), before + 1)

    def test_decide_denied_to_students_and_other_supervisors(self):
        for user in (self.student, self.other_supervisor):
            self.client.force_login(user)
            response = self.client.post(
                reverse("projects:proposal_decide", args=[self.proposal.pk]),
                {"decision": "approve"},
            )
            self.assertEqual(response.status_code, 403, f"{user} should be denied")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProjectProposal.Status.PENDING)

    def test_proposals_scoped_for_students(self):
        other = User.objects.create_user(username="other", email="other@example.com", password="x")
        other.role = User.Role.STUDENT
        other.save()
        ProjectProposal.objects.create(
            student=other, supervisor=self.supervisor, title="Other idea", description="Not mine."
        )
        self.client.force_login(self.student)
        response = self.client.get(reverse("projects:proposal_list"))
        self.assertEqual(response.context["proposals"].count(), 1)

    def test_supervisor_sees_only_proposals_sent_to_them(self):
        other = User.objects.create_user(username="other", email="other@example.com", password="x")
        other.role = User.Role.STUDENT
        other.save()
        ProjectProposal.objects.create(
            student=other, supervisor=self.other_supervisor, title="Not mine", description="For sup2."
        )
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("projects:proposal_list"))
        titles = [p.title for p in response.context["proposals"]]
        self.assertIn("Campus Navigator", titles)
        self.assertNotIn("Not mine", titles)

    def test_proposal_detail_view_student_can_open(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        doc = SimpleUploadedFile("proposal.pdf", b"file-content", content_type="application/pdf")
        self.proposal.proposal_document = doc
        self.proposal.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse("projects:proposal_detail", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus Navigator")
        self.assertContains(response, "Attached Document")

    def test_proposal_detail_view_student_cannot_open_others(self):
        other = User.objects.create_user(username="other", email="other@example.com", password="x")
        other.role = User.Role.STUDENT
        other.save()
        self.client.force_login(other)
        response = self.client.get(reverse("projects:proposal_detail", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 403)

    def test_proposal_detail_view_supervisor_can_open(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("projects:proposal_detail", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approve Proposal")
        self.assertContains(response, "Decline Proposal")

    def test_proposal_detail_view_other_supervisor_denied(self):
        self.client.force_login(self.other_supervisor)
        response = self.client.get(reverse("projects:proposal_detail", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 403)

    def test_proposal_detail_decide_from_detail_page(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:proposal_decide", args=[self.proposal.pk]),
            {"decision": "approve", "decision_note": "Looks good."},
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProjectProposal.Status.APPROVED)

    def test_proposal_list_shows_view_button(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse("projects:proposal_list"))
        self.assertContains(response, "View")

    def test_proposal_create_with_document(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_login(self.student)
        doc = SimpleUploadedFile("my_plan.pdf", b"plan-content", content_type="application/pdf")
        response = self.client.post(
            reverse("projects:proposal_create"),
            {
                "supervisor": self.supervisor.pk,
                "title": "AI Tutor",
                "description": "An AI-based tutoring system.",
                "proposal_document": doc,
            },
        )
        self.assertRedirects(response, reverse("projects:proposal_list"))
        proposal = ProjectProposal.objects.get(title="AI Tutor")
        self.assertTrue(proposal.proposal_document)
        self.assertTrue(proposal.proposal_document.name.endswith(".pdf"))

    def test_student_can_edit_declined_proposal(self):
        self.proposal.status = ProjectProposal.Status.DECLINED
        self.proposal.supervisor_feedback = "Narrow the scope."
        self.proposal.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse("projects:proposal_update", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Proposal")

    def test_edit_resubmits_to_pending(self):
        self.proposal.status = ProjectProposal.Status.DECLINED
        self.proposal.supervisor_feedback = "Revise."
        self.proposal.save()
        self.client.force_login(self.student)
        self.client.post(
            reverse("projects:proposal_update", args=[self.proposal.pk]),
            {
                "supervisor": self.supervisor.pk,
                "title": "Campus Navigator v2",
                "description": "Updated campus map.",
            },
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, ProjectProposal.Status.PENDING)
        self.assertEqual(self.proposal.supervisor_feedback, "")
        self.assertIsNone(self.proposal.reviewed_by)

    def test_edit_denied_for_non_owner(self):
        self.proposal.status = ProjectProposal.Status.DECLINED
        self.proposal.save()
        other = User.objects.create_user(username="other", email="other@example.com", password="x")
        other.role = User.Role.STUDENT
        other.save()
        self.client.force_login(other)
        response = self.client.get(reverse("projects:proposal_update", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 403)

    def test_edit_denied_when_not_declined(self):
        self.proposal.status = ProjectProposal.Status.PENDING
        self.proposal.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse("projects:proposal_update", args=[self.proposal.pk]))
        self.assertEqual(response.status_code, 403)

    def test_project_detail_hides_approve_decline_after_decision(self):
        from django.utils import timezone as tz
        self.client.force_login(self.supervisor)
        project = Project.objects.create(
            title="Decided Project", owner=self.student, supervisor=self.supervisor,
            approval_status=Project.ApprovalStatus.DECLINED, decided_by=self.supervisor,
            decided_at=tz.now(),
        )
        response = self.client.get(reverse("projects:project_detail", args=[project.pk]))
        self.assertNotContains(response, "value=\"approve\"")
        self.assertNotContains(response, "value=\"decline\"")


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

    def test_task_create_allowed_for_manager(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:task_create", args=[self.project.pk]),
            {"title": "Supervisor task", "assignee": self.member.pk, "priority": Task.Priority.HIGH},
        )
        self.assertTrue(Task.objects.filter(project=self.project, title="Supervisor task").exists())
        self.assertRedirects(response, reverse("projects:project_detail", args=[self.project.pk]))

    def test_task_create_denied_to_member(self):
        self.client.force_login(self.member)
        before = Task.objects.count()
        response = self.client.post(
            reverse("projects:task_create", args=[self.project.pk]),
            {"title": "Student task", "assignee": self.member.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Task.objects.count(), before)

    def test_assignee_queryset_excludes_supervisor(self):
        from .forms import project_user_queryset

        ids = set(project_user_queryset(self.project).values_list("id", flat=True))
        self.assertNotIn(self.supervisor.id, ids)
        self.assertIn(self.member.id, ids)
        self.assertIn(self.owner.id, ids)

    def test_task_create_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            reverse("projects:task_create", args=[self.project.pk]),
            {"title": "New task", "assignee": self.member.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_task_edit_allowed_for_supervisor(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse("projects:task_update", args=[self.task.pk]),
            {"title": "Edited", "assignee": self.member.pk, "priority": Task.Priority.MEDIUM, "status": Task.Status.IN_PROGRESS},
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Edited")
        self.assertRedirects(response, reverse("projects:project_detail", args=[self.project.pk]))

    def test_task_edit_denied_to_student_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("projects:task_update", args=[self.task.pk]))
        self.assertEqual(response.status_code, 403)

    def test_task_edit_denied_for_outsider(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:task_update", args=[self.task.pk]))
        self.assertEqual(response.status_code, 403)

    def test_task_delete(self):
        self.client.force_login(self.supervisor)
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
