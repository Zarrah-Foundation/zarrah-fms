from django.contrib import admin

from audit.models import ActivityLog, LoginHistory, Notification, NotificationRead


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "entity", "entity_id", "created_at")
    list_filter = ("action", "entity")
    search_fields = ("user__email", "description", "entity_id")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "logged_in_at", "expires_at")
    list_filter = ("logged_in_at",)
    search_fields = ("user__email", "ip_address")
    readonly_fields = ("logged_in_at",)
    raw_id_fields = ("user",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "target_role", "user", "is_read", "created_at")
    list_filter = ("type", "target_role", "is_read")
    search_fields = ("title", "message")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("notification", "user", "read_at")
    search_fields = ("user__email", "notification__title")
    raw_id_fields = ("notification", "user")
