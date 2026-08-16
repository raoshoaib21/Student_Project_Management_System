from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from core.models import Notification, log_activity
from projects.models import Project
from projects.permissions import is_project_member, scoped_projects

from .forms import FeedbackForm, ProgressReportForm
from .models import Feedback, ProgressReport
from .permissions import FeedbackPermissionMixin, ReportAccessMixin, ReportManageMixin, can_give_feedback

User = get_user_model()


class ProgressReportListView(LoginRequiredMixin, ListView):
    model = ProgressReport
    template_name = "progress/report_list.html"
    context_object_name = "reports"
    paginate_by = 12

    def get_queryset(self):
        qs = ProgressReport.objects.filter(
            project__in=scoped_projects(self.request.user)
        ).select_related("project", "author")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        project_id = self.request.GET.get("project", "")
        if q:
            qs = qs.filter(Q(summary__icontains=q) | Q(project__title__icontains=q))
        if status in ProgressReport.Status.values:
            qs = qs.filter(status=status)
        if project_id.isdigit():
            qs = qs.filter(project_id=project_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "progress"
        context["status_choices"] = ProgressReport.Status.choices
        context["projects"] = scoped_projects(self.request.user)
        return context


class ProgressReportCreateView(LoginRequiredMixin, CreateView):
    model = ProgressReport
    form_class = ProgressReportForm
    template_name = "progress/report_form.html"

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def dispatch(self, request, *args, **kwargs):
        if not is_project_member(request.user, self.get_project()):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.author = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, "created progress report", str(self.object), self.object.project.title)
        messages.success(self.request, f"Week {self.object.week_number} report created.")
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "progress"
        context["project"] = self.get_project()
        context["page_title"] = f"New Weekly Report — {self.get_project().title}"
        return context


class ProgressReportDetailView(ReportAccessMixin, DetailView):
    model = ProgressReport
    template_name = "progress/report_detail.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "progress"
        context["feedbacks"] = self.object.feedbacks.select_related("author")
        context["can_give_feedback"] = can_give_feedback(self.request.user, self.object)
        context["feedback_form"] = FeedbackForm() if context["can_give_feedback"] else None
        context["can_edit"] = self.request.user.id == self.object.author_id
        return context

    def post(self, request, *args, **kwargs):
        """Supervisor submits feedback on this report."""
        self.object = self.get_object()
        if not can_give_feedback(request.user, self.object):
            raise PermissionDenied
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.author = request.user
            feedback.project = self.object.project
            feedback.progress_report = self.object
            feedback.save()
            log_activity(request.user, "gave feedback", f"Week {self.object.week_number} of {self.object.project.title}")
            if self.object.author_id:
                Notification.objects.create(
                    user=self.object.author,
                    title="Feedback received",
                    message=f"{request.user} left feedback on your Week {self.object.week_number} report.",
                    url=self.object.get_absolute_url(),
                )
            messages.success(request, "Feedback submitted.")
            return HttpResponseRedirect(self.object.get_absolute_url())
        context = self.get_context_data(object=self.object)
        context["feedback_form"] = form
        return self.render_to_response(context)


class ProgressReportUpdateView(ReportManageMixin, UpdateView):
    model = ProgressReport
    form_class = ProgressReportForm
    template_name = "progress/report_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.object.project
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, "updated progress report", str(self.object))
        messages.success(self.request, "Report updated.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "progress"
        context["project"] = self.object.project
        context["page_title"] = f"Edit Week {self.object.week_number} Report"
        return context


class ProgressReportDeleteView(ReportManageMixin, DeleteView):
    model = ProgressReport
    template_name = "progress/report_confirm_delete.html"

    def get_success_url(self):
        return reverse("progress:report_list")

    def form_valid(self, form):
        label = str(self.object)
        response = super().form_valid(form)
        log_activity(self.request.user, "deleted progress report", label)
        messages.success(self.request, "Progress report deleted.")
        return response


@login_required
@require_POST
def report_submit(request, pk):
    """The report's author moves it from Draft to Submitted."""
    report = get_object_or_404(ProgressReport, pk=pk)
    user = request.user
    if user.id != report.author_id:
        raise PermissionDenied
    if report.status == ProgressReport.Status.DRAFT:
        report.status = ProgressReport.Status.SUBMITTED
        report.save(update_fields=["status", "updated_at"])
        log_activity(user, "submitted progress report", str(report))
        Notification.objects.create(
            user=report.project.supervisor,
            title="Progress report submitted",
            message=f"{report.author} submitted Week {report.week_number} of {report.project.title}.",
            url=report.get_absolute_url(),
        )
        messages.success(request, "Report submitted for supervisor review.")
    return HttpResponseRedirect(report.get_absolute_url())


@login_required
@require_POST
def report_review(request, pk):
    """Supervisor approves a report or sends it back for revision."""
    report = get_object_or_404(ProgressReport, pk=pk)
    if not can_give_feedback(request.user, report):
        raise PermissionDenied
    action = request.POST.get("action")
    if report.status == ProgressReport.Status.SUBMITTED and action in ("approve", "revision"):
        if action == "approve":
            report.status = ProgressReport.Status.APPROVED
            headline = "approved"
            verb = "approved"
        else:
            report.status = ProgressReport.Status.NEEDS_REVISION
            headline = "requested revision"
            verb = "requested revision on"
        report.save(update_fields=["status", "updated_at"])
        log_activity(request.user, verb, str(report))
        if report.author_id:
            Notification.objects.create(
                user=report.author,
                title=f"Report {headline}",
                message=f"Your Week {report.week_number} report was {headline} by {request.user}.",
                url=report.get_absolute_url(),
            )
        messages.success(request, f"Report marked as {report.get_status_display()}.")
    return HttpResponseRedirect(report.get_absolute_url())
