import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_migrate_images(apps, schema_editor):
    HomepageSectionImage = apps.get_model("cms", "HomepageSectionImage")
    CmsMedia = apps.get_model("cms", "CmsMedia")
    for row in HomepageSectionImage.objects.all():
        image_name = row.image.name if row.image else ""
        if not image_name:
            # Orphan row without a file — drop it so media can become non-null.
            row.delete()
            continue
        media = CmsMedia.objects.create(
            id=uuid.uuid4(),
            image=image_name,
            original_filename=image_name.rsplit("/", 1)[-1][:255],
            alt_en=row.alt_en or "",
            alt_bn=row.alt_bn or "",
            caption_en=row.caption_en or "",
            caption_bn=row.caption_bn or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        row.media_id = media.id
        row.save(update_fields=["media_id"])


def backwards_restore_images(apps, schema_editor):
    HomepageSectionImage = apps.get_model("cms", "HomepageSectionImage")
    for row in HomepageSectionImage.objects.select_related("media").all():
        if row.media_id and row.media and row.media.image:
            row.image = row.media.image.name
            row.save(update_fields=["image"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cms", "0004_homepage_cms_config_gallery_and_news_bilingual"),
    ]

    operations = [
        migrations.CreateModel(
            name="CmsMedia",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("image", models.ImageField(upload_to="cms/gallery/")),
                ("original_filename", models.CharField(blank=True, default="", max_length=255)),
                ("alt_en", models.CharField(blank=True, default="", max_length=200)),
                ("alt_bn", models.CharField(blank=True, default="", max_length=200)),
                ("caption_en", models.CharField(blank=True, default="", max_length=300)),
                ("caption_bn", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cms_media_uploads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "CMS media",
                "verbose_name_plural": "CMS media",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="homepagesectionimage",
            name="media",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="gallery_usages",
                to="cms.cmsmedia",
            ),
        ),
        migrations.RunPython(forwards_migrate_images, backwards_restore_images),
        migrations.AlterField(
            model_name="homepagesectionimage",
            name="media",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="gallery_usages",
                to="cms.cmsmedia",
            ),
        ),
        migrations.RemoveField(
            model_name="homepagesectionimage",
            name="image",
        ),
        migrations.AddConstraint(
            model_name="homepagesectionimage",
            constraint=models.UniqueConstraint(
                fields=("section", "media"), name="uniq_homepage_section_media"
            ),
        ),
    ]
