import django.db.models.deletion
from django.db import migrations, models

NOTIFICATION_PRIORITY_CHOICES = [
    ("LOW", "Low"),
    ("NORMAL", "Normal"),
    ("HIGH", "High"),
    ("CRITICAL", "Critical"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("audit", "0002_alter_notification_target_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="priority",
            field=models.CharField(choices=NOTIFICATION_PRIORITY_CHOICES, db_index=True, default="NORMAL", max_length=20),
        ),
        migrations.AddField(
            model_name="notification",
            name="icon",
            field=models.CharField(blank=True, default="", help_text="Bootstrap Icons class; auto-derived from type when blank.", max_length=80),
        ),
        migrations.AddField(
            model_name="notification",
            name="link",
            field=models.CharField(blank=True, default="", help_text="Optional target URL opened when the notification is clicked.", max_length=500),
        ),
        migrations.AddField(
            model_name="notification",
            name="object_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="content_type",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="contenttypes.contenttype"),
        ),
        migrations.AlterModelOptions(
            name="notification",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["is_read"], name="audit_notif_is_read_2b8f4a_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["priority"], name="audit_notif_priorit_6d1c3e_idx"),
        ),
    ]
