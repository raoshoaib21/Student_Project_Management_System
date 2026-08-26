from django.contrib import admin

from .models import Project, ProjectMember, ProjectProposal, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "supervisor", "status", "approval_status", "grade", "created_at")
    list_filter = ("status", "approval_status", "start_date", "due_date")
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


@admin.register(ProjectProposal)
class ProjectProposalAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "supervisor", "status", "reviewed_at", "created_at")
    list_filter = ("status", "created_at", "reviewed_at")
    search_fields = ("title", "description", "student__username", "supervisor__username")
    readonly_fields = ("student", "reviewed_by", "reviewed_at", "project")
