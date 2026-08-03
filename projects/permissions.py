"""Object-level authorization helpers and CBV mixins for projects and tasks."""

from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Project


def is_project_manager(user, project):
    """Owner or supervisor of the project (full control)."""
    return bool(user.is_authenticated and (project.owner_id == user.id or project.supervisor_id == user.id))


def is_project_leader(user, project):
    """User is a Leader member of the project."""
    return bool(user.is_authenticated and project.members.filter(user=user, role="LEADER").exists())


def is_project_member(user, project):
    """Owner, supervisor or member can access the project."""
    if not user.is_authenticated:
        return False
    if project.owner_id == user.id or project.supervisor_id == user.id:
        return True
    return project.members.filter(user=user).exists()


def scoped_projects(user):
    """Queryset of projects the user may see (data-level scoping)."""
    if not user.is_authenticated:
        return Project.objects.none()
    if user.is_supervisor:
        return Project.objects.filter(
            Q(supervisor=user) | Q(owner=user) | Q(members__user=user)
        ).distinct()
    return Project.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()


class ProjectViewAccessMixin:
    """Allow project members to view; everyone else gets 403."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not is_project_member(self.request.user, obj):
            raise PermissionDenied
        return obj


class ProjectManageAccessMixin:
    """Allow only the owner or supervisor to edit/delete."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not is_project_manager(self.request.user, obj):
            raise PermissionDenied
        return obj


class TaskAccessMixin:
    """Manage a task: managers always; other members only if they created it."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not is_project_member(user, obj.project):
            raise PermissionDenied
        if not is_project_manager(user, obj.project) and not is_project_leader(user, obj.project):
            if user.id != obj.created_by_id:
                raise PermissionDenied
        return obj
