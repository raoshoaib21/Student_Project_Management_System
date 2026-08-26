from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="project_list"),
    path("create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("proposals/", views.ProposalListView.as_view(), name="proposal_list"),
    path("proposals/create/", views.ProposalCreateView.as_view(), name="proposal_create"),
    path("proposals/<int:pk>/", views.proposal_detail_view, name="proposal_detail"),
    path("proposals/<int:pk>/decide/", views.proposal_decide, name="proposal_decide"),
    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="project_update"),
    path("<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),
    path("<int:pk>/members/", views.ProjectMembersView.as_view(), name="project_members"),
    path("<int:pk>/decide/", views.project_decide, name="project_decide"),
    path("<int:pk>/grade/", views.project_grade, name="project_grade"),
    path("<int:project_pk>/tasks/create/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task_update"),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    path("tasks/<int:pk>/status/", views.task_status, name="task_status"),
]
