from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from accounts.permissions import RoleRequiredMixin
from core.models import Notification, log_activity

from .forms import (
    ProjectDecisionForm,
    ProjectForm,
    ProjectGradeForm,
    ProjectMemberForm,
    ProjectProposalForm,
    TaskForm,
)
from .models import Project, ProjectMember, ProjectProposal, Task
from .permissions import (
    ProjectManageAccessMixin,
    ProjectViewAccessMixin,
    TaskAccessMixin,
    is_project_manager,
    is_project_member,
    is_project_supervisor,
    scoped_projects,
)


def proposal_detail_view(request, pk):
    """Supervisor: review proposal + download document + decide.
    Student: view own proposal status and feedback."""
    proposal = get_object_or_404(
        ProjectProposal.objects.select_related("student", "supervisor", "reviewed_by", "project"),
        pk=pk,
    )
    user = request.user
    if user.is_student and proposal.student_id != user.id:
        raise PermissionDenied
    if user.is_supervisor and proposal.supervisor_id != user.id:
        raise PermissionDenied

    if request.method == "POST" and user.is_supervisor and proposal.status == ProjectProposal.Status.PENDING:
        form = ProjectDecisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["decision"]
            feedback = form.cleaned_data["decision_note"]
            proposal.supervisor_feedback = feedback
            proposal.reviewed_by = user
            proposal.reviewed_at = timezone.now()

            if decision == "approve":
                if not proposal.project:
                    project = Project.objects.create(
                        title=proposal.title,
                        description=proposal.description,
                        owner=user,
                        supervisor=user,
                    )
                    ProjectMember.objects.create(
                        project=project, user=proposal.student, role=ProjectMember.Role.LEADER,
                    )
                    proposal.project = project
                proposal.status = ProjectProposal.Status.APPROVED
                log_activity(user, "approved proposal", proposal.title)
                Notification.objects.create(
                    user=proposal.student,
                    title="Proposal approved",
                    message=f"{user} approved your proposal '{proposal.title}'. The project is now assigned to you.",
                    url=proposal.project.get_absolute_url() if proposal.project else reverse("projects:project_list"),
                )
                messages.success(request, f"Proposal approved — '{proposal.title}' is now an assigned project.")
            else:
                proposal.status = ProjectProposal.Status.DECLINED
                log_activity(user, "declined proposal", proposal.title)
                Notification.objects.create(
                    user=proposal.student,
                    title="Proposal declined",
                    message=f"{user} declined your proposal '{proposal.title}'."
                    + (f" Feedback: {feedback}" if feedback else ""),
                    url=reverse("projects:proposal_list"),
                )
                messages.success(request, f"Proposal '{proposal.title}' declined with feedback.")
            proposal.save()
            return HttpResponseRedirect(reverse("projects:proposal_list"))
    else:
        form = ProjectDecisionForm()

    return render(request, "projects/proposal_detail.html", {
        "proposal": proposal,
        "decision_form": form,
        "active_page": "proposals",
    })

User = get_user_model()


def _notify(user, title, message, url):
    Notification.objects.create(user=user, title=title, message=message, url=url)


def _task_priority_order():
    return Case(
        *[When(priority=p, then=Value(i)) for i, p in enumerate(Task.Priority.values)],
        default=Value(len(Task.Priority.values)),
        output_field=IntegerField(),
    )


class ProjectListView(LoginRequiredMixin,ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 10

    def get_queryset(self):
        qs = scoped_projects(self.request.user).select_related("owner", "supervisor")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status in Project.Status.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "projects"
        context["status_choices"] = Project.Status.choices
        return context


class ProjectCreateView(RoleRequiredMixin, CreateView):
    """Projects are assigned by supervisors; students cannot self-create."""

    roles = (User.Role.SUPERVISOR,)
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, "created project", self.object.title)
        _notify(
            self.object.supervisor,
            "New project created",
            f"{self.request.user} created project '{self.object.title}' under your supervision.",
            self.object.get_absolute_url(),
        )
        messages.success(self.request, f"Project '{self.object.title}' created.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "projects"
        context["page_title"] = "New Project"
        return context


class ProjectDetailView(LoginRequiredMixin,ProjectViewAccessMixin, DetailView):
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "projects"
        context["members"] = self.object.members.select_related("user")
        context["tasks"] = self.object.tasks.select_related("assignee").order_by("status", _task_priority_order())
        context["is_manager"] = is_project_manager(self.request.user, self.object)
        context["is_assigned_supervisor"] = is_project_supervisor(self.request.user, self.object)
        context["decision_form"] = ProjectDecisionForm()
        context["grade_form"] = ProjectGradeForm(instance=self.object)

        tasks = list(self.object.tasks.select_related("assignee"))
        done = sum(1 for t in tasks if t.status == Task.Status.DONE)
        in_progress = sum(1 for t in tasks if t.status == Task.Status.IN_PROGRESS or t.status == Task.Status.REVIEW)
        total = len(tasks)
        context["tasks_total"] = total
        context["tasks_done"] = done
        context["tasks_in_progress"] = in_progress
        context["tasks_remaining"] = total - done
        context["tasks_progress"] = round(done / total * 100) if total else 0

        submissions = self.object.documents.filter(
            category="FINAL_SUBMISSION"
        ).select_related("uploaded_by")
        context["final_submissions"] = submissions
        context["my_final_submission"] = next(
            (d for d in submissions if d.uploaded_by_id == self.request.user.id), None
        )
        context["task_status_choices"] = Task.Status.choices
        context["documents"] = self.object.documents.select_related("uploaded_by")[:5]
        context["documents_count"] = self.object.documents.count()
        context["reports"] = self.object.progress_reports.select_related("author")[:5]
        context["reports_count"] = self.object.progress_reports.count()
        return context


class ProjectUpdateView(LoginRequiredMixin,ProjectManageAccessMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, "updated project", self.object.title)
        messages.success(self.request, "Project updated.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "projects"
        context["page_title"] = f"Edit Project: {self.object.title}"
        return context


class ProjectDeleteView(LoginRequiredMixin,ProjectManageAccessMixin, DeleteView):
    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("projects:project_list")

    def form_valid(self, form):
        log_activity(self.request.user, "deleted project", self.object.title)
        messages.success(self.request, f"Project '{self.object.title}' deleted.")
        return super().form_valid(form)


class ProjectMembersView(LoginRequiredMixin,FormView):
    """Add and remove project members (manager only)."""

    template_name = "projects/project_members.html"
    form_class = ProjectMemberForm

    def get_object(self):
        project = get_object_or_404(Project, pk=self.kwargs["pk"])
        if not is_project_manager(self.request.user, project):
            raise PermissionDenied
        return project

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        context["active_page"] = "projects"
        context["project"] = project
        context["members"] = project.members.select_related("user").order_by("-role", "user__username")
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        member_id = request.POST.get("remove_member_id")
        if member_id:
            member = get_object_or_404(ProjectMember, pk=member_id, project=self.object)
            if member.user_id == self.object.owner_id:
                messages.error(request, "The project owner cannot be removed.")
                return HttpResponseRedirect(reverse("projects:project_members", args=[self.object.pk]))
            member.delete()
            log_activity(request.user, "removed member", f"{member.user} from {self.object.title}")
            messages.success(request, f"{member.user} removed from the project.")
            return HttpResponseRedirect(reverse("projects:project_members", args=[self.object.pk]))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        project = self.get_object()
        member = form.save(commit=False)
        member.project = project
        member.save()
        log_activity(self.request.user, "added member", f"{member.user} to {project.title}")
        _notify(
            member.user,
            "Added to a project",
            f"You were added as a member of '{project.title}'.",
            project.get_absolute_url(),
        )
        messages.success(self.request, f"{member.user} added as {member.get_role_display()}.")
        return HttpResponseRedirect(reverse("projects:project_members", args=[project.pk]))


class ProposalListView(LoginRequiredMixin, ListView):
    """Students see their own proposals; supervisors review all of them."""

    model = ProjectProposal
    template_name = "projects/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 15

    def get_queryset(self):
        qs = ProjectProposal.objects.select_related("student", "supervisor", "reviewed_by", "project")
        if self.request.user.is_student:
            qs = qs.filter(student=self.request.user)
        else:
            qs = qs.filter(supervisor=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "proposals"
        context["decision_form"] = ProjectDecisionForm()
        return context


class ProposalCreateView(RoleRequiredMixin, CreateView):
    """Students pitch what they want to build; supervisors cannot propose."""

    roles = (User.Role.STUDENT,)
    model = ProjectProposal
    form_class = ProjectProposalForm
    template_name = "projects/proposal_form.html"

    def form_valid(self, form):
        form.instance.student = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, "submitted project proposal", self.object.title)
        Notification.objects.create(
            user=self.object.supervisor,
            title="New project proposal",
            message=f"{self.request.user} submitted a proposal '{self.object.title}' for your review.",
            url=reverse("projects:proposal_detail", args=[self.object.pk]),
        )
        messages.success(self.request, f"Proposal sent to {self.object.supervisor} for review.")
        return response

    def get_success_url(self):
        return reverse("projects:proposal_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "proposals"
        context["page_title"] = "Project Proposal"
        return context


class ProposalUpdateView(LoginRequiredMixin, UpdateView):
    """Students can edit a declined proposal and resubmit it for review."""

    model = ProjectProposal
    form_class = ProjectProposalForm
    template_name = "projects/proposal_form.html"

    def dispatch(self, request, *args, **kwargs):
        proposal = self.get_object()
        if request.user != proposal.student:
            raise PermissionDenied
        if proposal.status != ProjectProposal.Status.DECLINED:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.status = ProjectProposal.Status.PENDING
        form.instance.supervisor_feedback = ""
        form.instance.reviewed_by = None
        form.instance.reviewed_at = None
        response = super().form_valid(form)
        log_activity(self.request.user, "resubmitted project proposal", self.object.title)
        Notification.objects.create(
            user=self.object.supervisor,
            title="Proposal resubmitted",
            message=f"{self.request.user} resubmitted the proposal '{self.object.title}' for your review.",
            url=reverse("projects:proposal_detail", args=[self.object.pk]),
        )
        messages.success(self.request, f"Proposal resubmitted to {self.object.supervisor} for review.")
        return response

    def get_success_url(self):
        return reverse("projects:proposal_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "proposals"
        context["page_title"] = "Edit Proposal"
        return context


@login_required
@require_POST
def proposal_decide(request, pk):
    """The selected supervisor approves (auto-creating the assigned project) or declines with feedback."""
    proposal = get_object_or_404(ProjectProposal, pk=pk)
    if not is_project_supervisor(request.user, proposal):
        raise PermissionDenied
    form = ProjectDecisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid decision request.")
        return HttpResponseRedirect(reverse("projects:proposal_list"))

    decision = form.cleaned_data["decision"]
    feedback = form.cleaned_data["decision_note"]
    proposal.supervisor_feedback = feedback
    proposal.reviewed_by = request.user
    proposal.reviewed_at = timezone.now()

    if decision == "approve":
        if not proposal.project:
            project = Project.objects.create(
                title=proposal.title,
                description=proposal.description,
                owner=request.user,
                supervisor=request.user,
            )
            ProjectMember.objects.create(
                project=project, user=proposal.student, role=ProjectMember.Role.LEADER
            )
            proposal.project = project
        proposal.status = ProjectProposal.Status.APPROVED
        log_activity(request.user, "approved proposal", proposal.title)
        Notification.objects.create(
            user=proposal.student,
            title="Proposal approved",
            message=f"{request.user} approved your proposal '{proposal.title}'. The project is now assigned to you.",
            url=proposal.project.get_absolute_url() if proposal.project else reverse("projects:project_list"),
        )
        messages.success(request, f"Proposal approved — '{proposal.title}' is now an assigned project.")
    else:
        proposal.status = ProjectProposal.Status.DECLINED
        log_activity(request.user, "declined proposal", proposal.title)
        Notification.objects.create(
            user=proposal.student,
            title="Proposal declined",
            message=f"{request.user} declined your proposal '{proposal.title}'."
            + (f" Feedback: {feedback}" if feedback else ""),
            url=reverse("projects:proposal_list"),
        )
        messages.success(request, f"Proposal '{proposal.title}' declined with feedback.")
    proposal.save()
    return HttpResponseRedirect(reverse("projects:proposal_list"))


class TaskListView(LoginRequiredMixin,ListView):
    model = Task
    template_name = "projects/task_list.html"
    context_object_name = "tasks"
    paginate_by = 15

    def get_queryset(self):
        projects = scoped_projects(self.request.user)
        qs = Task.objects.filter(project__in=projects).select_related("project", "assignee")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        priority = self.request.GET.get("priority", "")
        assigned = self.request.GET.get("assigned", "")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status in Task.Status.values:
            qs = qs.filter(status=status)
        if priority in Task.Priority.values:
            qs = qs.filter(priority=priority)
        if assigned == "me":
            qs = qs.filter(assignee=self.request.user)
        return qs.order_by("status", _task_priority_order())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "tasks"
        context["status_choices"] = Task.Status.choices
        context["priority_choices"] = Task.Priority.choices
        return context


class TaskCreateView(LoginRequiredMixin,CreateView):
    model = Task
    form_class = TaskForm
    template_name = "projects/task_form.html"

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def dispatch(self, request, *args, **kwargs):
        project = self.get_project()
        if not is_project_supervisor(request.user, project):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        project = self.get_project()
        form.instance.project = project
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, "created task", self.object.title, f"in {project.title}")
        if self.object.assignee and self.object.assignee_id != self.request.user.id:
            _notify(
                self.object.assignee,
                "New task assigned",
                f"You were assigned task '{self.object.title}' in {project.title}.",
                project.get_absolute_url(),
            )
        messages.success(self.request, f"Task '{self.object.title}' created.")
        return response

    def get_success_url(self):
        return reverse("projects:project_detail", args=[self.kwargs["project_pk"]])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_project()
        context["active_page"] = "projects"
        context["project"] = project
        context["page_title"] = f"New Task in {project.title}"
        return context


class TaskUpdateView(LoginRequiredMixin,TaskAccessMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "projects/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_object().project
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, "updated task", self.object.title)
        messages.success(self.request, "Task updated.")
        return response

    def get_success_url(self):
        return reverse("projects:project_detail", args=[self.object.project_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "projects"
        context["project"] = self.object.project
        context["page_title"] = f"Edit Task: {self.object.title}"
        return context


class TaskDeleteView(LoginRequiredMixin,TaskAccessMixin, DeleteView):
    model = Task
    template_name = "projects/task_confirm_delete.html"

    def get_success_url(self):
        return reverse("projects:project_detail", args=[self.object.project_id])

    def form_valid(self, form):
        log_activity(self.request.user, "deleted task", self.object.title)
        messages.success(self.request, f"Task '{self.object.title}' deleted.")
        return super().form_valid(form)


@login_required
@require_POST
def task_status(request, pk):
    """Update a task's status (project members only)."""
    task = get_object_or_404(Task, pk=pk)
    if not is_project_member(request.user, task.project):
        raise PermissionDenied
    status = request.POST.get("status")
    if status in Task.Status.values and status != task.status:
        old_status = task.get_status_display()
        task.status = status
        task.save(update_fields=["status", "updated_at"])
        log_activity(request.user, "changed task status", task.title, f"{old_status} -> {task.get_status_display()}")
        messages.success(request, f"Task '{task.title}' moved to {task.get_status_display()}.")
    return HttpResponseRedirect(reverse("projects:project_detail", args=[task.project_id]))


def _notify_project_circle(project, title, message):
    """Notify the owner and every member of the project."""
    recipient_ids = set(project.members.values_list("user_id", flat=True))
    recipient_ids.add(project.owner_id)
    for user_id in recipient_ids:
        Notification.objects.create(user_id=user_id, title=title, message=message, url=project.get_absolute_url())


@login_required
@require_POST
def project_decide(request, pk):
    """Supervisor approves or declines a project against the requirements."""
    project = get_object_or_404(Project, pk=pk)
    if not is_project_supervisor(request.user, project):
        raise PermissionDenied
    form = ProjectDecisionForm(request.POST)
    if form.is_valid():
        decision = form.cleaned_data["decision"]
        project.approval_status = (
            Project.ApprovalStatus.APPROVED if decision == "approve" else Project.ApprovalStatus.DECLINED
        )
        project.decision_note = form.cleaned_data["decision_note"]
        project.decided_by = request.user
        project.decided_at = timezone.now()
        project.save(update_fields=["approval_status", "decision_note", "decided_by", "decided_at", "updated_at"])
        verb = "approved" if decision == "approve" else "declined"
        log_activity(request.user, f"{verb} project", project.title)
        _notify_project_circle(
            project,
            f"Project {verb}",
            f"{request.user} {verb} the project '{project.title}'."
            + (f" Note: {project.decision_note}" if project.decision_note else ""),
        )
        messages.success(request, f"Project '{project.title}' {verb}.")
    else:
        messages.error(request, "Invalid decision request.")
    return HttpResponseRedirect(reverse("projects:project_detail", args=[project.pk]))


@login_required
@require_POST
def project_grade(request, pk):
    """Supervisor records the final grade for a project."""
    project = get_object_or_404(Project, pk=pk)
    if not is_project_supervisor(request.user, project):
        raise PermissionDenied
    form = ProjectGradeForm(request.POST, instance=project)
    if form.is_valid():
        project = form.save(commit=False)
        project.graded_by = request.user
        project.graded_at = timezone.now()
        project.save(update_fields=["grade", "grade_comment", "graded_by", "graded_at", "updated_at"])
        log_activity(request.user, "graded project", project.title, f"Grade: {project.grade}")
        _notify_project_circle(
            project,
            "Project graded",
            f"{request.user} graded '{project.title}': {project.grade}.",
        )
        messages.success(request, f"Grade '{project.grade}' recorded for '{project.title}'.")
    else:
        messages.error(request, "Please select a valid grade.")
    return HttpResponseRedirect(reverse("projects:project_detail", args=[project.pk]))
