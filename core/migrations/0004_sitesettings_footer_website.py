from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_sync_foundation_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="website_url",
            field=models.URLField(blank=True, default="", verbose_name="Website URL"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="footer_text_bn",
            field=models.TextField(blank=True, default="", verbose_name="Footer Text (Bangla)"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="footer_text_en",
            field=models.TextField(blank=True, default="", verbose_name="Footer Text (English)"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="copyright_text",
            field=models.CharField(blank=True, default="", help_text="Shown in the footer. Leave blank to auto-generate from the foundation name.", max_length=300, verbose_name="Copyright Text"),
        ),
    ]
