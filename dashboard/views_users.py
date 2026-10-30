"""Administration: user management and RBAC role management.

Users keep their legacy ``accounts.User.role`` (single value) while also
holding any number of ``rbac.Role`` assignments via ``UserRole``. Role editing
manages the permission matrix over the seeded ``rbac.Permission`` catalog.
"""

import secrets
from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.models import Role as LegacyRole
from accounts.models import User
from audit.models import LoginHistory
from dashboard.forms import RoleForm, SetPasswordForm, UserCreateForm, UserEditForm
from rbac.models import Permission, Role as RbacRole, UserRole
from rbac.permissions import has_action
from rbac.registry import MODULES


# =========================================================================
# Users
# =========================================================================

@login_required
def users_list(request):
    if not has_action(request.user, "users", "view"):
        return redirect("dashboard")
    qs = User.objects.all().order_by("-created_at")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    active = request.GET.get("active", "").strip()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(name__icontains=q))
    if role:
        qs = qs.filter(role=role)
    if active == "1":
        qs = qs.filter(is_active_member=True)
    elif active == "0":
        qs = qs.filter(is_active_member=False)
    page_obj = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/users/list.html",
        {
            "page_obj": page_obj,
            "users": page_obj.object_list,
            "search_query": q,
            "role": role,
            "active": active,
            "roles": LegacyRole.choices,
            "can_create": has_action(request.user, "users", "create"),
            "can_edit": has_action(request.user, "users", "edit"),
        },
    )


def _sync_user_roles(user, roles, assigned_by):
    """Reconcile a user's UserRole rows to match ``roles`` (a queryset/list)."""
    target = {r.pk for r in roles}
    current = set(UserRole.objects.filter(user=user).values_list("role_id", flat=True))
    for role_id in current - target:
        UserRole.objects.filter(user=user, role_id=role_id).delete()
    for role in roles:
        if role.pk not in current:
            UserRole.objects.create(user=user, role=role, assigned_by=assigned_by)


@login_required
def user_create(request):
    if not has_action(request.user, "users", "create"):
        return redirect("dashboard")
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            raw_password = form.cleaned_data.get("password1") or secrets.token_urlsafe(10)
            user.set_password(raw_password)
            user.save()
            _sync_user_roles(user, form.cleaned_data["rbac_roles"], request.user)
            try:
                from audit.notifications import ADMIN_ROLES, NotificationType, notify_roles

                notify_roles(
                    ADMIN_ROLES,
                    title="User created",
                    message=f"{user.email} was created.",
                    ntype=NotificationType.USER_CREATED,
                    related_object=user,
                )
            except Exception:
                pass
            if not form.cleaned_data.get("password1"):
                messages.success(request, _("User created. Temporary password: %(pw)s") % {"pw": raw_password})
            else:
                messages.success(request, _("User created successfully."))
            return redirect("dashboard-user-edit", pk=user.pk)
    else:
        form = UserCreateForm()
    return render(request, "dashboard/users/form.html", {"form": form, "is_create": True})


@login_required
def user_edit(request, pk):
    if not has_action(request.user, "users", "edit"):
        return redirect("dashboard")
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            _sync_user_roles(user, form.cleaned_data["rbac_roles"], request.user)
            messages.success(request, _("User updated successfully."))
            return redirect("dashboard-user-edit", pk=user.pk)
    else:
        form = UserEditForm(
            instance=user,
            initial={"rbac_roles": RbacRole.objects.filter(user_assignments__user=user)},
        )
    logins = LoginHistory.objects.filter(user=user).order_by("-logged_in_at")[:20]
    return render(
        request,
        "dashboard/users/form.html",
        {
            "form": form,
            "is_create": False,
            "target_user": user,
            "login_history": logins,
            "can_reset": has_action(request.user, "users", "reset_password"),
            "can_deactivate": has_action(request.user, "users", "deactivate"),
        },
    )


@login_required
@require_POST
def user_toggle_active(request, pk):
    if not has_action(request.user, "users", "deactivate"):
        return redirect("dashboard")
    user = get_object_or_404(User, pk=pk)
    user.is_active_member = not user.is_active_member
    user.save(update_fields=["is_active_member"])
    if user.is_active_member:
        messages.success(request, _("User activated."))
    else:
        messages.success(request, _("User deactivated."))
    return redirect("dashboard-user-edit", pk=pk)


@login_required
def user_reset_password(request, pk):
    if not has_action(request.user, "users", "reset_password"):
        return redirect("dashboard")
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["password1"])
            user.save(update_fields=["password"])
            messages.success(request, _("Password reset successfully."))
            return redirect("dashboard-user-edit", pk=pk)
    else:
        form = SetPasswordForm()
    return render(
        request,
        "dashboard/users/reset_password.html",
        {"form": form, "target_user": user},
    )


# =========================================================================
# Roles & permissions
# =========================================================================

@login_required
def roles_list(request):
    if not has_action(request.user, "roles", "view"):
        return redirect("dashboard")
    roles = (
        RbacRole.objects.all()
        .annotate(n_users=Count("user_assignments", distinct=True))
        .order_by("name")
    )
    return render(
        request,
        "dashboard/users/roles_list.html",
        {
            "roles": roles,
            "can_create": has_action(request.user, "roles", "create"),
            "can_edit": has_action(request.user, "roles", "edit"),
            "can_delete": has_action(request.user, "roles", "delete"),
        },
    )


def _permission_groups(selected_ids=None):
    """Return OrderedDict(module_label -> [Permission]) following registry order."""
    selected = {str(x) for x in (selected_ids or set())}
    all_perms = list(Permission.objects.all())
    by_code = {p.codename: p for p in all_perms}
    groups = OrderedDict()
    for module, meta in MODULES.items():
        items = []
        for action in meta["actions"]:
            perm = by_code.get(f"{module}.{action}")
            if perm:
                items.append({"perm": perm, "checked": str(perm.id) in selected})
        if items:
            groups[meta["label"]] = items
    return groups


@login_required
def role_create(request):
    if not has_action(request.user, "roles", "create"):
        return redirect("dashboard")
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Role created successfully."))
            return redirect("dashboard-roles")
        selected_ids = set(request.POST.getlist("permissions"))
    else:
        form = RoleForm()
        selected_ids = set()
    return render(
        request,
        "dashboard/users/role_form.html",
        {"form": form, "is_create": True, "permission_groups": _permission_groups(selected_ids)},
    )


@login_required
def role_edit(request, pk):
    if not has_action(request.user, "roles", "edit"):
        return redirect("dashboard")
    role = get_object_or_404(RbacRole, pk=pk)
    if request.method == "POST":
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, _("Role updated successfully."))
            return redirect("dashboard-roles")
        selected_ids = set(role.permissions.values_list("id", flat=True))
    else:
        form = RoleForm(instance=role)
        selected_ids = set(role.permissions.values_list("id", flat=True))
    return render(
        request,
        "dashboard/users/role_form.html",
        {
            "form": form,
            "is_create": False,
            "role": role,
            "permission_groups": _permission_groups(selected_ids),
        },
    )


@login_required
@require_POST
def role_delete(request, pk):
    if not has_action(request.user, "roles", "delete"):
        return redirect("dashboard")
    role = get_object_or_404(RbacRole, pk=pk)
    if role.is_system:
        messages.error(request, _("System roles cannot be deleted."))
        return redirect("dashboard-roles")
    role.delete()
    messages.success(request, _("Role deleted."))
    return redirect("dashboard-roles")
