from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ApiKey, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin for the custom User model.
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


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    """
    Admin for API keys.

    Keys are generated here (not self-service) -- the raw token is shown once, in the
    success message after creation, and never again.
    """

    list_display = ["name", "user", "prefix", "created", "last_used"]
    list_filter = ["user"]
    search_fields = ["name", "user__email", "prefix"]
    autocomplete_fields = ["user"]
    readonly_fields = ["prefix", "hashed_key", "created", "last_used"]
    fields = ["user", "name", "prefix", "hashed_key", "created", "last_used"]

    def save_model(self, request, obj, form, change):
        if not change:
            raw_token, obj.prefix, obj.hashed_key = ApiKey.generate()
            self._generated_token = raw_token
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        token = getattr(self, "_generated_token", None)
        if token:
            messages.warning(
                request,
                f"API key for {obj.user}: {token} "
                "-- copy it now, it will not be shown again.",
            )
        return super().response_add(request, obj, post_url_continue)
