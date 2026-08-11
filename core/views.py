from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from projects.models import Task
from projects.permissions import scoped_projects

from .models import Notification


def health(request):
    return HttpResponse("ok")


class LandingView(TemplateView):
    template_name = "core/landing.html"


@login_required
def dashboard(request):
    user = request.user
    projects = scoped_projects(user).prefetch_related("members", "tasks")
    tasks = Task.objects.filter(project__in=projects)

    my_tasks = tasks.filter(assignee=user) if user.is_student else Task.objects.none()

    context = {
        "active_page": "dashboard",
        "projects": projects,
        "total_projects": projects.count(),
        "total_tasks": tasks.count(),
        "pending_tasks": tasks.exclude(status=Task.Status.DONE).count(),
        "completed_tasks": tasks.filter(status=Task.Status.DONE).count(),
        "my_tasks": my_tasks,
        "recent_activities": user.activities.all()[:10],
    }
    return render(request, "core/dashboard.html", context)


@login_required
def notification_list(request):
    notifications = request.user.notifications.all()
    filter_type = request.GET.get("filter", "")
    if filter_type == "unread":
        notifications = notifications.filter(is_read=False)
    elif filter_type == "read":
        notifications = notifications.filter(is_read=True)
    context = {
        "active_page": "notifications",
        "notifications": notifications,
        "unread_count": request.user.notifications.filter(is_read=False).count(),
        "filter_type": filter_type,
    }
    return render(request, "core/notification_list.html", context)


@login_required
def notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    if notification.url:
        return redirect(notification.url)
    return redirect("core:notification_list")


@login_required
@require_POST
def notification_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("core:notification_list")


@login_required
def activity_log(request):
    user = request.user
    activities = user.activities.all()
    q = request.GET.get("q", "").strip()
    if q:
        activities = activities.filter(action__icontains=q)
    context = {
        "active_page": "activity_log",
        "activities": activities,
        "q": q,
    }
    return render(request, "core/activity_log.html", context)
