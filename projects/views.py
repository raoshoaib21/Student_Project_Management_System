from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from core.models import Notification, log_activity

from .forms import ProjectForm, ProjectMemberForm, TaskForm
from .models import Project, ProjectMember, Task
from .permissions import (
    ProjectManageAccessMixin,
    ProjectViewAccessMixin,
    TaskAccessMixin,
    is_project_manager,
    is_project_member,
    scoped_projects,
)

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


class ProjectCreateView(LoginRequiredMixin,CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        if self.request.user.is_student:
            ProjectMember.objects.get_or_create(
                project=self.object, user=self.request.user, defaults={"role": ProjectMember.Role.LEADER}
            )
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
        if not is_project_member(request.user, project):
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
