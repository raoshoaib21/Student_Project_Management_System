from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "uploaded_by", "size", "file_type", "uploaded_at")
    list_filter = ("file_type", "uploaded_at")
    search_fields = ("name", "description", "project__title", "uploaded_by__username")
