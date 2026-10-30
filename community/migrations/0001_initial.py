import uuid

from django.db import migrations, models

VOLUNTEER_STATUS_CHOICES = [
    ("NEW", "New"),
    ("CONTACTED", "Contacted"),
    ("ACTIVE", "Active"),
    ("REJECTED", "Rejected"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=300)),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(fields=["is_read"], name="community_c_is_read_7a1c2d_idx"),
        ),
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(fields=["created_at"], name="community_c_created_3b9e1a_idx"),
        ),
        migrations.CreateModel(
            name="Volunteer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=20)),
                ("area_of_interest", models.CharField(blank=True, default="", max_length=200)),
                ("message", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=VOLUNTEER_STATUS_CHOICES, default="NEW", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="volunteer",
            index=models.Index(fields=["status"], name="community_v_status_5c2f8b_idx"),
        ),
        migrations.AddIndex(
            model_name="volunteer",
            index=models.Index(fields=["created_at"], name="community_v_created_9d4a2e_idx"),
        ),
        migrations.CreateModel(
            name="Testimonial",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("author_name", models.CharField(max_length=200)),
                ("designation", models.CharField(blank=True, default="", max_length=200)),
                ("content_bn", models.TextField(blank=True, default="")),
                ("content_en", models.TextField(blank=True, default="")),
                ("photo", models.ImageField(blank=True, null=True, upload_to="community/testimonials/")),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_published", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["display_order", "-created_at"]},
        ),
        migrations.CreateModel(
            name="FAQ",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("question_bn", models.CharField(blank=True, default="", max_length=300)),
                ("question_en", models.CharField(blank=True, default="", max_length=300)),
                ("answer_bn", models.TextField(blank=True, default="")),
                ("answer_en", models.TextField(blank=True, default="")),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["display_order"], "verbose_name": "FAQ", "verbose_name_plural": "FAQs"},
        ),
        migrations.CreateModel(
            name="Partner",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(blank=True, unique=True)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="community/partners/")),
                ("url", models.URLField(blank=True, default="")),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["display_order", "name"]},
        ),
    ]
