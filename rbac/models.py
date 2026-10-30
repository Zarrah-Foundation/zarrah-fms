import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from accounts.models import Role as LegacyRole


class Permission(models.Model):
    """A single action-based permission, e.g. ``members.approve``.

    Permissions are seeded from :mod:`rbac.registry` and are not meant to be
    hand-created; the ``codename`` is the stable identifier used everywhere in
    code (decorators, mixins, the ``{% can %}`` tag).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.CharField(max_length=50, db_index=True)
    action = models.CharField(max_length=50)
    codename = models.CharField(max_length=120, unique=True, editable=False)
    label = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["module", "action"]
        unique_together = [("module", "action")]
        indexes = [models.Index(fields=["module", "action"])]

    def save(self, *args, **kwargs):
        self.codename = f"{self.module}.{self.action}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codename


class Role(models.Model):
    """A named collection of permissions that can be assigned to many users.

    Unlimited roles are supported. ``is_system`` marks roles created by the
    seeder (safe defaults that shouldn't be deleted). ``legacy_role`` maps this
    role to the historical single-value ``accounts.User.role`` so existing
    accounts keep their access without any data migration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(
        default=False,
        help_text=_("System roles are created by the seeder and protected from deletion."),
    )
    is_active = models.BooleanField(default=True)
    legacy_role = models.CharField(
        max_length=50,
        choices=LegacyRole.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Maps this role to the legacy accounts.User.role value so existing "
            "users inherit its permissions automatically."
        ),
    )
    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        related_name="roles",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def permission_count(self):
        return self.permissions.count()

    @property
    def user_count(self):
        return self.user_assignments.count()


class RolePermission(models.Model):
    """Through model linking a Role to a Permission."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="permission_roles"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("role", "permission")]

    def __str__(self):
        return f"{self.role.name} -> {self.permission.codename}"


class UserRole(models.Model):
    """Assignment of a Role to a User. A user may hold many roles at once."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "role")]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user} = {self.role.name}"
