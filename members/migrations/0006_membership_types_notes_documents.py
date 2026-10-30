import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import core.validators

APPLICATION_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("UNDER_REVIEW", "Under Review"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
]


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("members", "0005_dropdowns_and_optional_email"),
    ]

    operations = [
        migrations.AlterField(
            model_name="memberapplication",
            name="status",
            field=models.CharField(choices=APPLICATION_STATUS_CHOICES, default="PENDING", max_length=20),
        ),
        migrations.CreateModel(
            name="MembershipType",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name_bn", models.CharField(max_length=150, verbose_name="Name (Bangla)")),
                ("name_en", models.CharField(max_length=150, verbose_name="Name (English)")),
                ("slug", models.SlugField(unique=True)),
                ("description_bn", models.TextField(blank=True, default="")),
                ("description_en", models.TextField(blank=True, default="")),
                ("fee_amount", models.FloatField(default=0, help_text="Default annual/one-time fee in BDT.")),
                ("is_lifetime", models.BooleanField(default=False)),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["display_order", "name_en"],
            },
        ),
        migrations.AddField(
            model_name="member",
            name="membership_type",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="members", to="members.membershiptype"),
        ),
        migrations.CreateModel(
            name="MemberNote",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="member_notes", to=settings.AUTH_USER_MODEL)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="members.member")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MemberDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("file", models.FileField(upload_to="members/documents/", validators=[core.validators.MaxFileSizeValidator(5), core.validators.FileTypeValidator(allowed_content_types=core.validators.ALLOWED_CONTENT_TYPES, allowed_extensions=core.validators.ALLOWED_EXTENSIONS)])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="members.member")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="uploaded_member_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
