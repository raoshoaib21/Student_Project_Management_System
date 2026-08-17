import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.core.mail.message import EmailMessage
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from core.models import log_activity

from .forms import (
    RegistrationForm,
    RememberMeAuthenticationForm,
    StudentProfileForm,
    SupervisorProfileForm,
    UserProfileForm,
)
from .models import StudentProfile, SupervisorProfile, User
from .tokens import EMAIL_TOKEN_MAX_AGE, generate_email_token, verify_email_token

logger = logging.getLogger(__name__)


class RegisterView(FormView):
    form_class = RegistrationForm
    template_name = "accounts/register.html"

    def form_valid(self, form):
        user = form.save()
        auth_login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        log_activity(user, "registered an account")
        messages.success(self.request, f"Welcome, {user.first_name or user.username}! Your account has been created.")
        return redirect("core:dashboard")


class RegisterDoneView(TemplateView):
    template_name = "accounts/register_done.html"


class VerifyEmailView(TemplateView):
    template_name = "accounts/verify_email.html"

    def get(self, request, *args, **kwargs):
        result = verify_email_token(kwargs["token"])
        user = None
        if result:
            pk, email = result
            user = User.objects.filter(pk=pk, email=email).first()
        if user and not user.is_email_verified:
            user.is_email_verified = True
            user.is_active = True
            user.save()
            log_activity(user, "verified email address")
            messages.success(request, "Email verified successfully. You can now log in.")
        elif user and user.is_email_verified:
            messages.info(request, "Your email was already verified.")
        else:
            messages.error(request, "The verification link is invalid or has expired.")
        return render(request, self.template_name, {"verified_user": user})


class CustomLoginView(LoginView):
    form_class = RememberMeAuthenticationForm

    def form_valid(self, form):
        if not form.cleaned_data.get("remember"):
            self.request.session.set_expiry(0)
        log_activity(form.get_user(), "logged in")
        return super().form_valid(form)


class CustomPasswordChangeView(PasswordChangeView):
    success_url = reverse_lazy("accounts:password_change_done")

    def form_valid(self, form):
        log_activity(self.request.user, "changed password")
        return super().form_valid(form)


@require_POST
def logout_view(request):
    user = request.user
    if user.is_authenticated:
        log_activity(user, "logged out")
    logout(request)
    return redirect("core:landing")


def profile(request):
    user = request.user
    profile_obj = None
    if user.is_student:
        profile_obj, _ = StudentProfile.objects.get_or_create(user=user)
        profile_form = StudentProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    else:
        profile_obj, _ = SupervisorProfile.objects.get_or_create(user=user)
        profile_form = SupervisorProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    user_form = UserProfileForm(request.POST or None, instance=user)

    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        log_activity(user, "updated profile")
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")

    context = {"user_form": user_form, "profile_form": profile_form}
    return render(request, "accounts/profile.html", context)
