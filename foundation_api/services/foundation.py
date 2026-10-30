from core.models import SiteSettings


class FoundationService:
    """Public read-only foundation data."""

    @staticmethod
    def get_settings():
        return SiteSettings.load()