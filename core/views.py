from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from projects.models import Task
from projects.permissions import scoped_projects


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
        "projects": projects,
        "total_projects": projects.count(),
        "total_tasks": tasks.count(),
        "pending_tasks": tasks.exclude(status=Task.Status.DONE).count(),
        "completed_tasks": tasks.filter(status=Task.Status.DONE).count(),
        "my_tasks": my_tasks,
        "recent_activities": user.activities.all()[:10],
    }
    return render(request, "core/dashboard.html", context)
