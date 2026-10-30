# Swaps the python-magic-based MIME sniffing validator usage for the
# dependency-free extension + content_type (+ Pillow for images) validators
# in core.validators. Validator changes are Python-level metadata only —
# no actual column/type change, so this migration is state-only.

import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0002_application_redesign"),
    ]

    operations = [
        migrations.AlterField(
            model_name="memberapplication",
            name="photo",
            field=models.ImageField(
                upload_to="members/photos/",
                validators=[
                    core.validators.MaxFileSizeValidator(3),
                    core.validators.ImageFileValidator(),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="identity_document",
            field=models.FileField(
                upload_to="members/identity/",
                validators=[
                    core.validators.MaxFileSizeValidator(3),
                    core.validators.FileTypeValidator(
                        allowed_extensions=core.validators.ALLOWED_EXTENSIONS,
                        allowed_content_types=core.validators.ALLOWED_CONTENT_TYPES,
                    ),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="cv",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="members/cv/",
                validators=[
                    core.validators.MaxFileSizeValidator(3),
                    core.validators.FileTypeValidator(
                        allowed_extensions=core.validators.ALLOWED_EXTENSIONS,
                        allowed_content_types=core.validators.ALLOWED_CONTENT_TYPES,
                    ),
                ],
            ),
        ),
    ]
