from django.contrib import admin

from community.models import (
    ContactMessage,
    FAQ,
    LeadershipPerson,
    Partner,
    Testimonial,
    Volunteer,
)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("subject", "name", "email", "message")


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "phone")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author_name", "designation", "is_published", "display_order")
    list_filter = ("is_published",)
    search_fields = ("author_name", "designation")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question_en", "is_active", "display_order")
    list_filter = ("is_active",)
    search_fields = ("question_en", "question_bn")


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "relationship_type", "is_active", "display_order")
    list_filter = ("is_active", "relationship_type")
    search_fields = ("name",)


@admin.register(LeadershipPerson)
class LeadershipPersonAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_published", "display_order")
    list_filter = ("role", "is_published")
    search_fields = ("name", "role_label_en", "role_label_bn")
