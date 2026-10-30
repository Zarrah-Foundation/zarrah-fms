from django.contrib import admin

from rbac.models import Permission, Role, RolePermission, UserRole


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ("permission",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "legacy_role", "is_system", "is_active", "permission_count", "user_count")
    list_filter = ("is_system", "is_active", "legacy_role")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "module", "action", "label")
    list_filter = ("module",)
    search_fields = ("codename", "module", "action", "label")
    readonly_fields = ("codename",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "assigned_by", "assigned_at")
    list_filter = ("role",)
    search_fields = ("user__email", "user__name", "role__name")
    raw_id_fields = ("user", "assigned_by")
    autocomplete_fields = ("role",)
