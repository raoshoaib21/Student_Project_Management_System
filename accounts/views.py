from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from core.models import log_activity

from .forms import (
    RememberMeAuthenticationForm,
    StudentProfileForm,
    SupervisorProfileForm,
    UserProfileForm,
)
from .models import StudentProfile, SupervisorProfile


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


@login_required
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
