from django.urls import path

from . import diagnostic, views

app_name = "core"

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path("_diag/", diagnostic.diagnosys, name="diagnosys"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
    path("notifications/read-all/", views.notification_read_all, name="notification_read_all"),
    path("activity-log/", views.activity_log, name="activity_log"),
]
