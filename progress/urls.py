from django.urls import path

from . import views

app_name = "progress"

urlpatterns = [
    path("", views.ProgressReportListView.as_view(), name="report_list"),
    path("create/<int:project_pk>/", views.ProgressReportCreateView.as_view(), name="report_create"),
    path("<int:pk>/", views.ProgressReportDetailView.as_view(), name="report_detail"),
    path("<int:pk>/edit/", views.ProgressReportUpdateView.as_view(), name="report_update"),
    path("<int:pk>/delete/", views.ProgressReportDeleteView.as_view(), name="report_delete"),
    path("<int:pk>/submit/", views.report_submit, name="report_submit"),
    path("<int:pk>/review/", views.report_review, name="report_review"),
]
