from django.contrib import admin

from .models import Feedback, ProgressReport


@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = ("project", "week_number", "author", "status", "created_at")
    list_filter = ("status", "week_number")
    search_fields = ("project__title", "author__username", "summary")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("author", "project", "progress_report", "created_at")
    search_fields = ("content", "author__username", "project__title")
