from django.conf import settings
from django.db import models


def project_file_path(instance, filename):
    return f"projects/{instance.project_id}/{filename}"


class Document(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
    )
    file = models.FileField(upload_to=project_file_path)
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    size = models.PositiveBigIntegerField(editable=False, default=0)
    file_type = models.CharField(max_length=50, blank=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name or self.file.name

    def save(self, *args, **kwargs):
        if self.file:
            self.size = self.file.size
            self.file_type = self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""
            if not self.name:
                self.name = self.file.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)
