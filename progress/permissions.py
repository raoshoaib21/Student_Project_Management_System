"""Object-level authorization helpers and CBV mixins for progress reports and feedback."""

from django.core.exceptions import PermissionDenied

from projects.permissions import is_project_manager


def can_give_feedback(user, report):
    """Only the project's supervisor may give feedback on its reports."""
    if not user.is_authenticated or not user.is_supervisor:
        return False
    return report.project.supervisor_id == user.id


class ReportAccessMixin:
    """Authors and project managers can access a progress report."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.id != obj.author_id and not is_project_manager(user, obj.project):
            raise PermissionDenied
        return obj


class FeedbackPermissionMixin:
    """Only the project's supervisor can create feedback on a report."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_give_feedback(self.request.user, obj):
            raise PermissionDenied
        return obj
