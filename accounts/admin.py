from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import StudentProfile, SupervisorProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_email_verified", "is_active", "is_staff")
    list_filter = ("role", "is_email_verified", "is_active", "is_staff")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Project PMS", {"fields": ("role", "is_email_verified")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Project PMS", {"fields": ("role", "is_email_verified")}),
    )
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "registration_number", "department", "course", "level")
    search_fields = ("user__username", "user__email", "registration_number")


@admin.register(SupervisorProfile)
class SupervisorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "department", "office")
    search_fields = ("user__username", "user__email", "title", "department")
