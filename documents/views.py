import mimetypes

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.models import Notification, log_activity
from projects.models import Project
from projects.permissions import is_project_member, scoped_projects

from .forms import DocumentForm
from .models import Document
from .permissions import DocumentAccessMixin, DocumentManageMixin, can_manage_document


def _notify_members(project, message, url, exclude=None):
    """Notify all members and the supervisor about a project change."""
    recipients = set(project.members.values_list("user_id", flat=True))
    recipients.update([project.owner_id, project.supervisor_id])
    if exclude is not None:
        recipients.discard(exclude)
    for user_id in recipients:
        Notification.objects.create(user_id=user_id, title="New document uploaded", message=message, url=url)


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 12

    def get_queryset(self):
        qs = Document.objects.filter(project__in=scoped_projects(self.request.user)).select_related(
            "project", "uploaded_by"
        )
        q = self.request.GET.get("q", "").strip()
        project_id = self.request.GET.get("project", "")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if project_id.isdigit():
            qs = qs.filter(project_id=project_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "documents"
        context["projects"] = scoped_projects(self.request.user)
        return context


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def dispatch(self, request, *args, **kwargs):
        if not is_project_member(request.user, self.get_project()):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        log_activity(self.request.user, "uploaded document", self.object.name, f"in {self.object.project.title}")
        _notify_members(
            self.object.project,
            f"{self.request.user} uploaded '{self.object.name}'.",
            reverse("documents:document_detail", args=[self.object.pk]),
            exclude=self.request.user.id,
        )
        messages.success(self.request, f"Document '{self.object.name}' uploaded.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "documents"
        context["project"] = self.get_project()
        context["page_title"] = f"Upload Document — {self.get_project().title}"
        return context


class DocumentDetailView(DocumentAccessMixin, DetailView):
    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "documents"
        context["can_manage"] = can_manage_document(self.request.user, self.object)
        return context


class DocumentUpdateView(DocumentManageMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "documents/document_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(self.request.user, "updated document", self.object.name)
        messages.success(self.request, "Document updated.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_page"] = "documents"
        context["project"] = self.object.project
        context["page_title"] = f"Edit Document — {self.object.name}"
        return context


class DocumentDeleteView(DocumentManageMixin, DeleteView):
    model = Document
    template_name = "documents/document_confirm_delete.html"
    success_url = reverse_lazy("documents:document_list")

    def form_valid(self, form):
        name = self.object.name
        response = super().form_valid(form)
        log_activity(self.request.user, "deleted document", name)
        messages.success(self.request, f"Document '{name}' deleted.")
        return response


class DocumentDownloadView(DocumentAccessMixin, DetailView):
    """Serve the raw file for project members."""

    model = Document
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        document = self.get_object()
        content_type, _ = mimetypes.guess_type(document.file.name)
        response = FileResponse(document.file.open("rb"), content_type=content_type or "application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{document.name}"'
        return response
