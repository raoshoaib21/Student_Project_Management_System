"""Object-level authorization helpers and CBV mixins for documents."""

from django.core.exceptions import PermissionDenied

from projects.permissions import is_project_manager, is_project_member


def can_manage_document(user, document):
    if is_project_manager(user, document.project):
        return True
    return document.uploaded_by_id == user.id


class DocumentAccessMixin:
    """View/download allowed for any project member."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not is_project_member(self.request.user, obj.project):
            raise PermissionDenied
        return obj


class DocumentManageMixin(DocumentAccessMixin):
    """Upload/update/delete allowed for managers or the uploader."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not can_manage_document(self.request.user, obj):
            raise PermissionDenied
        return obj
