"""Seed constitutional meeting types with quorum ratios."""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from governance.models import EligibilityMode, MeetingType

TYPES = [
    {
        "name_en": "Board Meeting",
        "name_bn": "বোর্ড সভা",
        "slug": "board",
        "quorum_numerator": 2,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.LINKED_GROUPS,
        "description_en": (
            "Board meetings require two-thirds (2/3) quorum per the constitution. "
            "Link eligible member groups after seeding."
        ),
        "display_order": 10,
    },
    {
        "name_en": "Executive Committee",
        "name_bn": "কার্যনির্বাহী কমিটি",
        "slug": "executive",
        "quorum_numerator": 2,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.LINKED_GROUPS,
        "description_en": (
            "Executive Committee meetings require two-thirds (2/3) of total members "
            "(constitution Art. meetings)."
        ),
        "display_order": 20,
    },
    {
        "name_en": "Advisory Board",
        "name_bn": "উপদেষ্টা পরিষদ",
        "slug": "advisory",
        "quorum_numerator": 2,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.LINKED_GROUPS,
        "description_en": (
            "Advisory Board meetings require two-thirds (2/3) quorum "
            "(constitution Art. meetings)."
        ),
        "display_order": 30,
    },
    {
        "name_en": "General Council",
        "name_bn": "সাধারণ পরিষদ",
        "slug": "general",
        "quorum_numerator": 1,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.ALL_APPROVED,
        "description_en": (
            "General Council meetings require one-third (1/3) of all approved members "
            "(constitution Art. meetings)."
        ),
        "display_order": 40,
    },
    {
        "name_en": "Annual General Meeting (AGM)",
        "name_bn": "বার্ষিক সাধারণ সভা (AGM)",
        "slug": "agm",
        "quorum_numerator": 1,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.ALL_APPROVED,
        "description_en": (
            "AGM quorum is one-third (1/3) of total enrolled members "
            "(constitution Art. meetings)."
        ),
        "display_order": 50,
    },
    {
        "name_en": "Emergency Meeting",
        "name_bn": "জরুরি সভা",
        "slug": "emergency",
        "quorum_numerator": 2,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.LINKED_GROUPS,
        "description_en": (
            "Emergency meetings use two-thirds (2/3) quorum unless constitution "
            "specifies otherwise for the convening body."
        ),
        "display_order": 60,
    },
    {
        "name_en": "Other",
        "name_bn": "অন্যান্য",
        "slug": "other",
        "quorum_numerator": 2,
        "quorum_denominator": 3,
        "eligibility_mode": EligibilityMode.LINKED_GROUPS,
        "description_en": (
            "Default two-thirds (2/3) quorum; adjust eligibility groups as needed."
        ),
        "display_order": 90,
    },
]


class Command(BaseCommand):
    help = "Seed meeting types with constitutional quorum ratios (idempotent)."

    def handle(self, *args, **options):
        created = updated = 0
        for row in TYPES:
            slug = row.get("slug") or slugify(row["name_en"])
            defaults = {
                k: v
                for k, v in row.items()
                if k not in ("slug",)
            }
            _, was_created = MeetingType.objects.update_or_create(
                slug=slug,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Meeting types: {created} created, {updated} updated."
            )
        )
