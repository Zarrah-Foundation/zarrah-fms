from django.db import migrations


def sync_identity(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    for obj in SiteSettings.objects.all():
        changed = False
        if obj.site_title and (
            not obj.foundation_name_en or obj.foundation_name_en == "Zarrah Foundation"
        ):
            obj.foundation_name_en = obj.site_title
            changed = True
        if obj.site_tagline and not obj.tagline_en:
            obj.tagline_en = obj.site_tagline
            changed = True
        if not obj.meta_title:
            obj.meta_title = obj.foundation_name_en or obj.site_title or ""
            changed = True
        if not obj.short_name:
            obj.short_name = obj.foundation_name_bn or obj.foundation_name_en or obj.site_title
            changed = True
        if changed:
            obj.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_foundation_smtp_donation_receipts"),
    ]

    operations = [
        migrations.RunPython(sync_identity, noop),
    ]
