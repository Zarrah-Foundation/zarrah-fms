"""Seed the action-based permission catalog and default system roles.

Idempotent for catalog creation. For system roles, grants are synchronized to
the declared list (extras are removed) so Phase 6C RBAC tightenings apply on
re-seed. User↔role assignments are never deleted.

    python manage.py seed_rbac
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role as LegacyRole
from rbac import registry
from rbac.models import Permission, Role, RolePermission

# "*" means every permission. A trailing ".*" means every action in a module.
ALL = "*"

# Default system roles. ``legacy_role`` wires the role to the historical
# accounts.User.role value so existing accounts inherit permissions with no
# data migration. The "example" roles (President, Secretary, ...) requested in
# the spec are also seeded, without a legacy mapping.
SYSTEM_ROLES = [
    {
        "name": "Super Admin",
        "legacy_role": LegacyRole.SUPER_ADMIN,
        "description": "Full, unrestricted access to every module and action.",
        "grants": [ALL],
    },
    {
        "name": "Executive Admin",
        "legacy_role": LegacyRole.EXECUTIVE_ADMIN,
        "description": "Broad administrative access across members, donations, finance and content.",
        "grants": [
            "dashboard.*", "members.*", "applications.*", "membership_types.*",
            "membership_fees.*", "donations.*", "donation_categories.*",
            "quick_amounts.*", "payment_methods.*", "finance.*", "news.*",
            "news_categories.*", "reports.*", "transparency.*", "volunteers.*",
            "testimonials.*", "contact_messages.*", "faqs.*", "partners.*",
            "cms.*", "site_settings.*", "voting.*", "elections.*", "notifications.*",
            "meetings.*", "resolutions.*", "resolution_documents.*",
            "resolution_public_sharing.*",
            "leadership.*",
            # Payment center — no refunds_approve (Super Admin only)
            "payments.view", "payments.manage", "payments.configuration",
            "payments.webhooks", "payments.refunds_view", "payments.refunds_request",
            "payments.recurring_view", "payments.recurring_manage",
            "payments.transactions_view", "payments.logs_view",
        ],
    },
    {
        "name": "Regional Admin",
        "legacy_role": LegacyRole.REGIONAL_ADMIN,
        "description": "Manage members and applications for a region.",
        "grants": [
            "dashboard.view", "members.*", "applications.*",
            "membership_fees.view", "reports.view", "notifications.view",
        ],
    },
    {
        "name": "News Editor",
        "legacy_role": LegacyRole.NEWS_EDITOR,
        "description": "Create and publish news; manage homepage content.",
        "grants": [
            "dashboard.view", "news.*", "news_categories.*", "cms.*",
            "notifications.view",
        ],
    },
    {
        "name": "Finance Officer",
        "legacy_role": LegacyRole.FINANCE_OFFICER,
        "description": "Manage finance entries, donations and financial reports.",
        "grants": [
            "dashboard.view", "finance.*", "donations.*", "donation_categories.*",
            "quick_amounts.*", "payment_methods.*", "membership_fees.*",
            "reports.*", "notifications.view",
            "payments.view", "payments.webhooks", "payments.refunds_view",
            "payments.refunds_request", "payments.recurring_view",
            "payments.transactions_view", "payments.logs_view",
        ],
    },
    {
        "name": "Volunteer Coordinator",
        "legacy_role": LegacyRole.VOLUNTEER_COORDINATOR,
        "description": "Manage volunteers. Election administration is reserved for Executive/Super Admin.",
        "grants": [
            "dashboard.view", "volunteers.*", "notifications.view",
        ],
    },
    {
        "name": "Member",
        "legacy_role": LegacyRole.MEMBER,
        "description": "Standard member dashboard access.",
        "grants": ["dashboard.view", "notifications.view"],
    },
    {
        "name": "Donor",
        "legacy_role": LegacyRole.DONOR,
        "description": "Standard donor dashboard access.",
        "grants": ["dashboard.view", "notifications.view"],
    },
    # --- Example organizational roles (no legacy mapping) ---
    {
        "name": "President",
        "description": "Executive leadership — full oversight.",
        "grants": [ALL],
    },
    {
        "name": "Secretary",
        "description": "Members, applications, news, reports and governance operations.",
        "grants": [
            "dashboard.view", "members.*", "applications.*", "membership_types.*",
            "news.*", "news_categories.*", "reports.*", "transparency.*",
            "notifications.view",
            "meetings.*", "resolutions.*", "resolution_documents.*",
            "resolution_public_sharing.*",
        ],
    },
    {
        "name": "Treasurer",
        "description": "Finance, donations and financial reporting.",
        "grants": [
            "dashboard.view", "finance.*", "donations.*", "donation_categories.*",
            "quick_amounts.*", "payment_methods.*", "membership_fees.*",
            "reports.*", "notifications.view",
        ],
    },
    {
        "name": "Membership Manager",
        "description": "Members, applications, types and fees.",
        "grants": [
            "dashboard.view", "members.*", "applications.*", "membership_types.*",
            "membership_fees.*", "notifications.view",
        ],
    },
    {
        "name": "Finance Manager",
        "description": "Full finance and reporting access.",
        "grants": [
            "dashboard.view", "finance.*", "reports.*", "membership_fees.*",
            "notifications.view",
        ],
    },
    {
        "name": "Donation Manager",
        "description": "Donations, categories, quick amounts and payment methods.",
        "grants": [
            "dashboard.view", "donations.*", "donation_categories.*",
            "quick_amounts.*", "payment_methods.*", "reports.view",
            "reports.export", "notifications.view",
        ],
    },
    {
        "name": "Editor",
        "description": "News and website content.",
        "grants": [
            "dashboard.view", "news.*", "news_categories.*", "cms.*",
            "notifications.view",
        ],
    },
    {
        "name": "Moderator",
        "description": "Community moderation — testimonials, FAQs, messages.",
        "grants": [
            "dashboard.view", "testimonials.*", "faqs.*", "contact_messages.*",
            "partners.*", "notifications.view",
        ],
    },
    {
        "name": "Volunteer Manager",
        "description": "Manage volunteers.",
        "grants": ["dashboard.view", "volunteers.*", "notifications.view"],
    },
]


class Command(BaseCommand):
    help = "Seed action-based permissions and default system roles (idempotent)."

    def handle(self, *args, **options):
        with transaction.atomic():
            perms_by_code = self._sync_permissions()
            self._sync_roles(perms_by_code)
        self.stdout.write(self.style.SUCCESS("RBAC seed complete."))

    def _sync_permissions(self):
        perms_by_code = {}
        created = 0
        for module, action, code, label in registry.iter_permissions():
            obj, was_created = Permission.objects.get_or_create(
                module=module,
                action=action,
                defaults={"label": label},
            )
            if not was_created and obj.label != label:
                obj.label = label
                obj.save(update_fields=["label", "codename"])
            perms_by_code[code] = obj
            created += int(was_created)
        self.stdout.write(f"Permissions: {len(perms_by_code)} total, {created} new.")
        return perms_by_code

    def _resolve_grants(self, grants, perms_by_code):
        """Expand grant patterns (``*``, ``module.*``, exact codenames) to Permission rows."""
        codes = set()
        for grant in grants:
            if grant == ALL:
                codes.update(perms_by_code.keys())
            elif grant.endswith(".*"):
                module = grant[:-2]
                codes.update(c for c in perms_by_code if c.startswith(f"{module}."))
            elif grant in perms_by_code:
                codes.add(grant)
            else:
                self.stdout.write(self.style.WARNING(f"  Unknown grant '{grant}' skipped."))
        return [perms_by_code[c] for c in codes]

    def _sync_roles(self, perms_by_code):
        for spec in SYSTEM_ROLES:
            role, _created = Role.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "description": spec.get("description", ""),
                    "is_system": True,
                    "legacy_role": spec.get("legacy_role"),
                },
            )
            # Keep system metadata in sync without clobbering admin edits to membership.
            changed = False
            if not role.is_system:
                role.is_system = True
                changed = True
            if spec.get("legacy_role") and role.legacy_role != spec.get("legacy_role"):
                role.legacy_role = spec["legacy_role"]
                changed = True
            if changed:
                role.save()

            wanted = self._resolve_grants(spec["grants"], perms_by_code)
            wanted_ids = {p.id for p in wanted}
            existing = set(
                RolePermission.objects.filter(role=role).values_list("permission_id", flat=True)
            )
            to_add = [p for p in wanted if p.id not in existing]
            RolePermission.objects.bulk_create(
                [RolePermission(role=role, permission=p) for p in to_add],
                ignore_conflicts=True,
            )
            to_remove = existing - wanted_ids
            removed = 0
            if to_remove:
                removed, _ = RolePermission.objects.filter(
                    role=role, permission_id__in=to_remove
                ).delete()
            self.stdout.write(
                f"Role '{role.name}': +{len(to_add)} / -{removed} permissions "
                f"({len(wanted)} total)."
            )
