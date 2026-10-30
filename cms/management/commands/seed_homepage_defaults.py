"""Seed idempotent default homepage CMS content.

Usage:
    python manage.py seed_homepage_defaults

Safe to run multiple times. Existing sections (matched by section_type + order)
and testimonials (matched by author_name) are never overwritten — including
publish/unpublish state and edited copy.
"""

from django.core.management.base import BaseCommand

from cms.homepage_defaults import seed_homepage_defaults


class Command(BaseCommand):
    help = "Create missing bilingual homepage default CMS sections (idempotent)."

    def handle(self, *args, **options):
        result = seed_homepage_defaults(verbosity=options.get("verbosity", 1))
        self.stdout.write(
            self.style.SUCCESS(
                "Homepage defaults: "
                f"{result['created_sections']} section(s) created, "
                f"{result['skipped_sections']} section(s) skipped; "
                f"{result['leadership_created']} leadership created; "
                f"{result['supporters_created']} supporter(s) created; "
                f"{result['skills_news_created']} skills news created; "
                f"{result['qa_news_unpublished']} QA news unpublished; "
                f"{result['unpublished_placeholder_testimonials']} empty/placeholder testimonial(s) unpublished."
            )
        )
