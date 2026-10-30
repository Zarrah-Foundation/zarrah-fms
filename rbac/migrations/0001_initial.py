import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

LEGACY_ROLE_CHOICES = [
    ("SUPER_ADMIN", "Super Admin"),
    ("EXECUTIVE_ADMIN", "Executive Admin"),
    ("REGIONAL_ADMIN", "Regional Admin"),
    ("NEWS_EDITOR", "News Editor"),
    ("FINANCE_OFFICER", "Finance Officer"),
    ("VOLUNTEER_COORDINATOR", "Volunteer Coordinator"),
    ("MEMBER", "Member"),
    ("DONOR", "Donor"),
]


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Permission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("module", models.CharField(db_index=True, max_length=50)),
                ("action", models.CharField(max_length=50)),
                ("codename", models.CharField(editable=False, max_length=120, unique=True)),
                ("label", models.CharField(blank=True, default="", max_length=200)),
            ],
            options={
                "ordering": ["module", "action"],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=120, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("is_system", models.BooleanField(default=False, help_text="System roles are created by the seeder and protected from deletion.")),
                ("is_active", models.BooleanField(default=True)),
                ("legacy_role", models.CharField(blank=True, choices=LEGACY_ROLE_CHOICES, db_index=True, help_text="Maps this role to the legacy accounts.User.role value so existing users inherit its permissions automatically.", max_length=50, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("permission", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permission_roles", to="rbac.permission")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_permissions", to="rbac.role")),
            ],
        ),
        migrations.AddField(
            model_name="role",
            name="permissions",
            field=models.ManyToManyField(blank=True, related_name="roles", through="rbac.RolePermission", to="rbac.permission"),
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="role_assignments_made", to=settings.AUTH_USER_MODEL)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_assignments", to="rbac.role")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_roles", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="permission",
            index=models.Index(fields=["module", "action"], name="rbac_permis_module_1d3d7e_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="permission",
            unique_together={("module", "action")},
        ),
        migrations.AlterUniqueTogether(
            name="rolepermission",
            unique_together={("role", "permission")},
        ),
        migrations.AddIndex(
            model_name="userrole",
            index=models.Index(fields=["user"], name="rbac_userro_user_id_0e6e7a_idx"),
        ),
        migrations.AddIndex(
            model_name="userrole",
            index=models.Index(fields=["role"], name="rbac_userro_role_id_9c2e1b_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="userrole",
            unique_together={("user", "role")},
        ),
    ]
