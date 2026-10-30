from rest_framework import serializers

from core.models import SiteSettings

from django.conf import settings

class AbsoluteImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None

        url = super().to_representation(value)

        if url.startswith("http://") or url.startswith("https://"):
            return url

        return settings.SITE_URL.rstrip("/") + url

class FoundationSerializer(serializers.ModelSerializer):

    logo = AbsoluteImageField(source="site_logo", read_only=True)
    dark_logo = AbsoluteImageField(read_only=True)
    logo_white = AbsoluteImageField(source="site_logo_white", read_only=True)
    favicon = AbsoluteImageField(source="site_favicon", read_only=True)
    twitter_card_image = AbsoluteImageField(read_only=True)

    email = serializers.CharField(source="primary_email")
    phone = serializers.CharField(source="primary_phone")
    website = serializers.CharField(source="website_url")

    class Meta:
        model = SiteSettings

        fields = (
            "foundation_name_en",
            "foundation_name_bn",
            "short_name",
            "foundation_description_en",
            "foundation_description_bn",
            "logo",
            "dark_logo",
            "logo_white",
            "favicon",
            "email",
            "phone",
            "whatsapp",
            "website",
            "address_en",
            "address_bn",
            "google_maps_embed_url",
            "facebook_url",
            "linkedin_url",
            "youtube_url",
            "instagram_url",
            "twitter_url",
            "office_hours",
            "registration_number",
            "registration_date",
            "copyright_text",
            "brand_primary_color",
            "brand_secondary_color",
            "twitter_card_image",
        )