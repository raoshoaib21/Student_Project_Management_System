from django.contrib import admin

from .models import Project, ProjectMember, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "supervisor", "status", "start_date", "due_date", "created_at")
    list_filter = ("status", "start_date", "due_date")
    search_fields = ("title", "description", "owner__username", "supervisor__username")
    inlines = [TaskInline]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("project__title", "user__username")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "assignee", "priority", "status", "due_date")
    list_filter = ("priority", "status", "due_date")
    search_fields = ("title", "description", "project__title", "assignee__username")
