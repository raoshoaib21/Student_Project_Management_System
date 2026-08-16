from django.conf import settings
from django.db import models


class ProgressReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        NEEDS_REVISION = "NEEDS_REVISION", "Needs Revision"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="progress_reports")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_reports",
    )
    week_number = models.PositiveIntegerField()
    summary = models.TextField()
    achievements = models.TextField(blank=True)
    next_week_plan = models.TextField(blank=True)
    blockers = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project", "week_number")
        ordering = ["-week_number"]

    def __str__(self):
        return f"Week {self.week_number} - {self.project}"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("progress:report_detail", args=[self.pk])


class Feedback(models.Model):
    progress_report = models.ForeignKey(
        ProgressReport,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="feedbacks",
        null=True,
        blank=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="given_feedbacks",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback by {self.author or 'deleted user'}"

    def save(self, *args, **kwargs):
        if self.progress_report_id:
            self.project = self.progress_report.project
        super().save(*args, **kwargs)
