from django.contrib import admin

from cms.models import CmsMedia, HomepageSection, HomepageSectionImage, ImpactStatistic


class HomepageSectionImageInline(admin.TabularInline):
    model = HomepageSectionImage
    extra = 0
    fields = ("media", "alt_en", "alt_bn", "caption_en", "caption_bn", "order", "is_active")
    raw_id_fields = ("media",)


@admin.register(CmsMedia)
class CmsMediaAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "image", "created_at", "uploaded_by")
    search_fields = ("original_filename", "caption_en", "caption_bn", "alt_en", "alt_bn")
    readonly_fields = ("created_at", "updated_at")


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ("section_type", "order", "title_en", "is_visible", "is_published", "is_deleted")
    list_filter = ("section_type", "is_visible", "is_published", "is_deleted")
    search_fields = ("title_en", "title_bn", "content_en", "content_bn")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("order",)
    inlines = [HomepageSectionImageInline]


@admin.register(ImpactStatistic)
class ImpactStatisticAdmin(admin.ModelAdmin):
    list_display = ("value", "label_en", "period_year", "display_order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("value", "label_en", "label_bn")
    ordering = ("display_order",)
