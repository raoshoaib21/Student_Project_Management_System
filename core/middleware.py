"""Custom login-required middleware with a public URL allowlist."""

from django.conf import settings
from django.contrib.auth.middleware import LoginRequiredMiddleware as DjangoLoginRequiredMiddleware
from django.urls import resolve


class LoginRequiredMiddleware(DjangoLoginRequiredMiddleware):
    """Like Django's built-in, but skips paths/views listed in settings.

    LOGIN_REQUIRED_IGNORE_PATHS      -> path prefixes allowed anonymously
    LOGIN_REQUIRED_IGNORE_VIEW_NAMES -> URL names allowed anonymously
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            return None

        path = request.path_info
        if any(path.startswith(prefix) for prefix in settings.LOGIN_REQUIRED_IGNORE_PATHS):
            return None

        view_name = resolve(request.path_info).url_name
        if view_name in settings.LOGIN_REQUIRED_IGNORE_VIEW_NAMES:
            return None

        return super().process_view(request, view_func, view_args, view_kwargs)
