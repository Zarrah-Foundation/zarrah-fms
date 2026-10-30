# Generated manually: adds News Editor, Finance Officer and Volunteer
# Coordinator roles for the role-based dashboard sidebar. Choice changes are
# state-only and require no actual column alteration.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("SUPER_ADMIN", "Super Admin"),
                    ("EXECUTIVE_ADMIN", "Executive Admin"),
                    ("REGIONAL_ADMIN", "Regional Admin"),
                    ("NEWS_EDITOR", "News Editor"),
                    ("FINANCE_OFFICER", "Finance Officer"),
                    ("VOLUNTEER_COORDINATOR", "Volunteer Coordinator"),
                    ("MEMBER", "Member"),
                    ("DONOR", "Donor"),
                ],
                db_index=True,
                default="MEMBER",
                max_length=20,
            ),
        ),
    ]
