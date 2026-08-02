from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin for the custom User model
    """

    list_display = ["email", "name", "is_active", "is_staff", "created"]
    list_filter = ["is_active", "is_staff", "is_superuser", "groups"]
    search_fields = ["email", "name"]
    ordering = ["email"]
    readonly_fields = ["last_login", "created"]

    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Personal info", {"fields": ["name"]}),
        (
            "Permissions",
            {
                "fields": [
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ],
            },
        ),
        ("Important dates", {"fields": ["last_login", "created"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "name", "password1", "password2"],
            },
        ),
    ]
