from django.db import migrations, models


EDUCATION_TYPE_CHOICES = [
    ("GENERAL", "General Education"),
    ("QAUMI", "Qaumi Madrasah"),
    ("ALIA", "Alia Madrasah"),
    ("TECHNICAL", "Technical / Vocational"),
]

EDUCATION_STATUS_CHOICES = [
    ("CURRENT", "Currently Studying"),
    ("COMPLETED", "Completed"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0005_dropdowns_and_optional_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="memberapplication",
            name="education_class",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="education_type",
            field=models.CharField(
                blank=True, choices=EDUCATION_TYPE_CHOICES, max_length=20, null=True
            ),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="education_status",
            field=models.CharField(
                blank=True, choices=EDUCATION_STATUS_CHOICES, max_length=20, null=True
            ),
        ),
    ]
