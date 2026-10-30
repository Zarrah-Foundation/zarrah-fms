from django.contrib import admin

from reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "type",
        "year",
        "is_public",
        "display_order",
        "published_at",
        "download_count",
        "uploaded_by",
    )
    list_filter = ("type", "year", "is_public")
    search_fields = ("title", "title_en", "title_bn", "description", "description_en", "description_bn")
    readonly_fields = ("download_count", "uploaded_at", "created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "title_en",
                    "title_bn",
                    "description",
                    "description_en",
                    "description_bn",
                    "type",
                    "year",
                    "file",
                    "is_public",
                    "published_at",
                    "display_order",
                )
            },
        ),
        (
            "Meta",
            {"fields": ("uploaded_by", "download_count", "uploaded_at", "created_at", "updated_at")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
