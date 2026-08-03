"""Role-based permission helpers for function and class-based views."""

from functools import wraps

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import User


def role_required(*roles):
    """Decorator: allow only users whose role is in ``roles`` (e.g. role_required("SUPERVISOR"))."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return user_passes_test(lambda u: False, login_url="accounts:login")(view_func)(request, *args, **kwargs)
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class RoleRequiredMixin(LoginRequiredMixin):
    """CBV mixin: set ``roles`` (tuple of User.Role values) to restrict access."""

    roles = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.roles and request.user.role not in self.roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
