"""Seed standard Zarrah Foundation organizational positions."""

from django.core.management.base import BaseCommand

from members.models import CouncilBody, OrganizationalPosition

DEFAULTS = [
    ("Chairman", "চেয়ারম্যান", CouncilBody.BOARD, 10),
    ("President", "সভাপতি", CouncilBody.EXECUTIVE, 20),
    ("Secretary", "সম্পাদক", CouncilBody.EXECUTIVE, 30),
    ("Treasurer", "কোষাধ্যক্ষ", CouncilBody.EXECUTIVE, 40),
    ("Executive Member", "কার্যনির্বাহী সদস্য", CouncilBody.EXECUTIVE, 50),
    ("Advisory Member", "উপদেষ্টা সদস্য", CouncilBody.ADVISORY, 60),
    ("General Member", "সাধারণ সদস্য", CouncilBody.GENERAL, 70),
]


class Command(BaseCommand):
    help = "Seed organizational position catalog (idempotent by name_en + council)."

    def handle(self, *args, **options):
        created = 0
        for name_en, name_bn, council, order in DEFAULTS:
            _, was_created = OrganizationalPosition.objects.get_or_create(
                name_en=name_en,
                council_body=council,
                defaults={
                    "name_bn": name_bn,
                    "display_order": order,
                    "is_active": True,
                    "is_primary_eligible": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(f"Organizational positions ready ({created} created).")
        )
