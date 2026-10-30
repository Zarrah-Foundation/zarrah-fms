from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import Role, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "name", "role", "is_active_member", "is_staff", "created_at")
    list_filter = ("role", "is_active_member", "is_staff", "is_superuser")
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("name", "image", "email_verified")}),
        ("Permissions", {"fields": ("role", "is_active_member", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Tokens", {"fields": ("reset_token", "reset_token_expiry", "email_verify_token", "email_verify_token_expiry")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "role")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login")
