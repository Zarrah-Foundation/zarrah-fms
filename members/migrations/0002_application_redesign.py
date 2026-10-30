# Generated manually for the membership application redesign
# (Tailwind build tooling was unavailable to run makemigrations interactively;
# hand-authored to exactly mirror what the autodetector would produce).

import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0001_initial"),
    ]

    operations = [
        # --- widen / relax existing fields ---
        migrations.AlterField(
            model_name="memberapplication",
            name="full_name",
            field=models.CharField(editable=False, max_length=200),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="identity_type",
            field=models.CharField(
                choices=[
                    ("NID", "NID"),
                    ("BIRTH_REGISTRATION", "Birth Registration"),
                    ("PASSPORT", "Passport"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="identity_document",
            field=models.FileField(
                upload_to="members/identity/",
                validators=[core.validators.MaxFileSizeValidator(3)],
            ),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="photo",
            field=models.ImageField(
                upload_to="members/photos/",
                validators=[core.validators.MaxFileSizeValidator(3)],
            ),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="present_division",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="present_district",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="present_upazila",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="present_union",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="present_address",
            field=models.TextField(blank=True, help_text="Village / Road / House", null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="occupation",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name="memberapplication",
            name="education",
            field=models.CharField(blank=True, editable=False, max_length=200),
        ),
        # --- personal information additions ---
        migrations.AddField(
            model_name="memberapplication",
            name="bangla_name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="english_name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="father_name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="mother_name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="marital_status",
            field=models.CharField(
                choices=[
                    ("SINGLE", "Single"),
                    ("MARRIED", "Married"),
                    ("DIVORCED", "Divorced"),
                    ("WIDOWED", "Widowed"),
                ],
                default="SINGLE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="religion",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        # --- expatriate additions ---
        migrations.AddField(
            model_name="memberapplication",
            name="expat_state_province",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="expat_city",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="expat_postal_code",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="passport_number",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        # --- occupation additions ---
        migrations.AddField(
            model_name="memberapplication",
            name="designation",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        # --- education additions ---
        migrations.AddField(
            model_name="memberapplication",
            name="education_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("GENERAL", "General"),
                    ("QAUMI", "Qaumi"),
                    ("ALIA", "Alia"),
                    ("TECHNICAL", "Technical"),
                    ("VOCATIONAL", "Vocational"),
                    ("OTHER", "Other"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="education_level",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="education_status",
            field=models.CharField(
                blank=True,
                choices=[("CURRENT", "Currently Studying"), ("COMPLETED", "Completed")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="education_institution",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="education_passing_year",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberapplication",
            name="education_result",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        # --- membership category ---
        migrations.AddField(
            model_name="memberapplication",
            name="membership_category",
            field=models.CharField(
                choices=[
                    ("GENERAL", "General Member"),
                    ("VOLUNTEER", "Volunteer"),
                    ("LIFETIME", "Lifetime Member"),
                    ("DONOR", "Donor"),
                    ("PATRON", "Patron"),
                    ("CORPORATE", "Corporate Member"),
                ],
                default="GENERAL",
                max_length=20,
            ),
        ),
        # --- optional CV upload ---
        migrations.AddField(
            model_name="memberapplication",
            name="cv",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="members/cv/",
                validators=[core.validators.MaxFileSizeValidator(3)],
            ),
        ),
    ]
