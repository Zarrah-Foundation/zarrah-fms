"""Membership module: members, membership types, applications, fees."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _, gettext_lazy as _l
from django.views.decorators.http import require_http_methods, require_POST

from audit.models import ActivityLog
from dashboard.crud import DashCreateView, DashDeleteView, DashListView, DashUpdateView
from dashboard.forms import (
    ApplicationEditForm,
    MemberDocumentForm,
    MemberEditForm,
    MemberNoteForm,
    MemberGroupForm,
    MemberPositionAssignForm,
    MemberPositionEditForm,
    MembershipFeeSettingsForm,
    MembershipTypeForm,
)
from members.forms import AdminMemberApplicationForm
from core.choices import DonationStatus, PaymentMethod
from members.audit_edits import (
    SENSITIVE_APPLICATION_FIELDS,
    SENSITIVE_MEMBER_FIELDS,
    apply_model_edits,
    compute_field_diffs,
    requires_reason,
)
from members.billing import (
    deactivate_autopay,
    ensure_ledger_months,
    get_or_create_autopay,
    paid_through,
    record_admin_fee_payment,
    record_admin_registration_fee_payment,
)
from members.documents import (
    generate_application_pdf,
    generate_bulk_applications_pdf,
    generate_bulk_members_pdf,
    generate_member_pdf,
)
from members.fee_settings import get_monthly_fee_amount
from members.fee_summary import (
    annotate_members_for_fee_list,
    summarize_member_fees,
    summaries_for_members,
)
from members.models import (
    ApplicationStatus,
    Member,
    MemberApplication,
    MemberGroup,
    MemberPositionAssignment,
    MembershipBillingEvent,
    MembershipFee,
    MembershipFeePayment,
    MembershipFeeSettings,
    MembershipRegistrationFee,
    MembershipType,
    MemberStatus,
)
from members.positions import (
    assign_position,
    effective_assignments,
    end_position,
    update_assignment,
)
from members.services import create_application_as_admin, request_missing_documents
from members.transitions import TransitionError, transition_application
from rbac.permissions import has_action


def _require(request, module, action):
    return has_action(request.user, module, action)


# =========================================================================
# Members
# =========================================================================

@login_required
def members_list(request):
    if not _require(request, "members", "view"):
        return redirect("dashboard")

    qs = Member.objects.select_related("user", "membership_type").order_by("-created_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if q:
        qs = qs.filter(
            Q(member_id__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(user__email__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/membership/members_list.html",
        {
            "page_obj": page_obj,
            "members": page_obj.object_list,
            "q": q,
            "status": status,
            "status_choices": MemberStatus.choices,
            "can_create": _require(request, "members", "create"),
            "can_edit": _require(request, "members", "edit"),
            "can_delete": _require(request, "members", "delete"),
        },
    )


def _edit_history_qs(entity: str, entity_id: str):
    return ActivityLog.objects.filter(
        entity=entity, entity_id=str(entity_id)
    ).select_related("user").order_by("-created_at")


def _can_view_sensitive_history(user) -> bool:
    return bool(
        getattr(user, "is_staff", False)
        or has_action(user, "members", "edit_sensitive")
        or has_action(user, "applications", "edit_sensitive")
    )


def _redact_history_values(log, *, can_view_sensitive: bool, sensitive_fields):
    """Hide sensitive old/new unless permitted; never expose private file paths."""
    old = dict(log.old_values or {})
    new = dict(log.new_values or {})
    for key in set(old) | set(new):
        if key in ("signature_image", "photo", "identity_document", "cv", "file"):
            old.pop(key, None)
            new.pop(key, None)
            continue
        if not can_view_sensitive and key in sensitive_fields:
            if key in old:
                old[key] = "••••"
            if key in new:
                new[key] = "••••"
    return old, new


@login_required
def member_detail(request, pk):
    if not _require(request, "members", "view"):
        return redirect("dashboard")
    member = get_object_or_404(
        Member.objects.select_related("user", "membership_type").prefetch_related(
            Prefetch(
                "position_assignments",
                queryset=MemberPositionAssignment.objects.select_related("position"),
            )
        ),
        pk=pk,
    )
    user = member.user

    ensure_ledger_months(member)
    fees = member.membership_fees.order_by("-year", "-month")
    fee_summary = summarize_member_fees(member, ensure_ledger=False)
    donations = user.donations.select_related("category").order_by("-created_at")[:20] if user else []
    notes = member.notes.select_related("author")
    documents = member.documents.all()
    login_history = user.login_history.order_by("-logged_in_at")[:10] if user else []
    timeline = ActivityLog.objects.filter(
        Q(entity="Member", entity_id=str(member.pk)) | Q(user=user)
    ).order_by("-created_at")[:30]
    autopay = get_or_create_autopay(member)
    pt = paid_through(member)

    effective = list(effective_assignments(member))
    all_assignments = list(
        member.position_assignments.select_related("position").order_by(
            "-start_date", "position__display_order"
        )
    )
    can_view_sensitive = _can_view_sensitive_history(request.user)
    history_qs = _edit_history_qs("Member", member.pk)
    history_page = Paginator(history_qs, 15).get_page(request.GET.get("history_page"))
    edit_history = []
    for log in history_page:
        old, new = _redact_history_values(
            log, can_view_sensitive=can_view_sensitive, sensitive_fields=SENSITIVE_MEMBER_FIELDS
        )
        changes = [
            {"field": key, "old": old.get(key), "new": new.get(key)}
            for key in sorted(set(old) | set(new))
        ]
        edit_history.append({"log": log, "changes": changes})

    # Roles: RBAC assignments + legacy role.
    roles = []
    try:
        from rbac.models import UserRole

        roles = list(UserRole.objects.filter(user=user).select_related("role"))
    except Exception:
        roles = []

    return render(
        request,
        "dashboard/membership/member_detail.html",
        {
            "member": member,
            "account": user,
            "fees": fees,
            "fee_summary": fee_summary,
            "donations": donations,
            "notes": notes,
            "documents": documents,
            "login_history": login_history,
            "timeline": timeline,
            "roles": roles,
            "note_form": MemberNoteForm(),
            "document_form": MemberDocumentForm(),
            "position_form": MemberPositionAssignForm(
                initial={"start_date": timezone.localdate()}
            ),
            "effective_assignments": effective,
            "all_assignments": all_assignments,
            "edit_history": edit_history,
            "edit_history_page": history_page,
            "autopay": autopay,
            "paid_through": pt,
            "monthly_fee": get_monthly_fee_amount(),
            "offline_methods": [
                (m.value, m.label)
                for m in PaymentMethod
                if m
                not in (
                    PaymentMethod.SSLCOMMERZ,
                )
            ],
            "can_edit": _require(request, "members", "edit"),
            "can_delete": _require(request, "members", "delete"),
            "can_manage_positions": _require(request, "members", "manage_positions"),
            "can_profile_download": _require(request, "members", "profile_download"),
            "can_record_fee": _require(request, "membership_fees", "create"),
            "can_manage_autopay": _require(request, "membership_fees", "edit"),
            "can_view_fees": _require(request, "membership_fees", "view"),
            "can_view_sensitive_history": can_view_sensitive,
        },
    )


@login_required
def member_create(request):
    if not _require(request, "members", "create"):
        return redirect("dashboard-members")
    if request.method == "POST":
        form = AdminMemberApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application, member = create_application_as_admin(
                form,
                creator=request.user,
                membership_type=form.cleaned_data.get("membership_type"),
                auto_approve=bool(form.cleaned_data.get("auto_approve")),
            )
            if member:
                messages.success(
                    request,
                    _("Member %(id)s created from application %(ref)s.")
                    % {"id": member.member_id, "ref": application.reference_code},
                )
                return redirect("dashboard-member-detail", pk=member.pk)
            messages.success(
                request,
                _("Application %(ref)s created and queued for review.")
                % {"ref": application.reference_code},
            )
            return redirect("dashboard-application-detail", pk=application.pk)
    else:
        form = AdminMemberApplicationForm()

    import json

    from core.education_data import EDUCATION_CLASSES, EDUCATION_STAGES, EDUCATION_TYPES

    return render(
        request,
        "dashboard/membership/member_create_application.html",
        {
            "form": form,
            "page_title": _("Add Member"),
            "cancel_url": _resolve("dashboard-members"),
            "education_data_json": json.dumps(
                {
                    "types": EDUCATION_TYPES,
                    "stages": EDUCATION_STAGES,
                    "classes": EDUCATION_CLASSES,
                }
            ),
        },
    )


@login_required
def member_edit(request, pk):
    if not _require(request, "members", "edit"):
        return redirect("dashboard-members")
    member = get_object_or_404(
        Member.objects.select_related("membership_type", "user"), pk=pk
    )
    can_edit_sensitive = _require(request, "members", "edit_sensitive")
    if request.method == "POST":
        form = MemberEditForm(request.POST, instance=member)
        if form.is_valid():
            cleaned = {
                k: form.cleaned_data[k]
                for k in form.Meta.fields
                if k in form.cleaned_data
            }
            diffs = compute_field_diffs(member, cleaned, cleaned.keys())
            sensitive = requires_reason(diffs, SENSITIVE_MEMBER_FIELDS)
            if sensitive and not can_edit_sensitive:
                messages.error(
                    request,
                    _("You do not have permission to change sensitive official fields."),
                )
            else:
                try:
                    apply_model_edits(
                        member,
                        cleaned,
                        actor=request.user,
                        entity="Member",
                        reason=form.cleaned_data.get("reason") or "",
                        sensitive_fields=SENSITIVE_MEMBER_FIELDS,
                        fields=cleaned.keys(),
                        request=request,
                    )
                    messages.success(request, _("Member updated."))
                    return redirect("dashboard-member-detail", pk=member.pk)
                except ValueError as exc:
                    messages.error(request, str(exc))
    else:
        form = MemberEditForm(instance=member)
    return render(
        request,
        "dashboard/membership/member_edit.html",
        {
            "form": form,
            "member": member,
            "can_edit_sensitive": can_edit_sensitive,
            "sensitive_fields": sorted(SENSITIVE_MEMBER_FIELDS),
        },
    )


@login_required
@require_POST
def member_position_assign(request, pk):
    if not _require(request, "members", "manage_positions"):
        return redirect("dashboard-member-detail", pk=pk)
    member = get_object_or_404(Member, pk=pk)
    form = MemberPositionAssignForm(request.POST)
    if form.is_valid():
        try:
            assign_position(
                member,
                form.cleaned_data["position"],
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data.get("end_date"),
                is_primary=bool(form.cleaned_data.get("is_primary")),
                notes=form.cleaned_data.get("notes") or "",
                actor=request.user,
                reason=form.cleaned_data.get("reason") or "",
            )
            messages.success(request, _("Position assigned."))
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, _("Could not assign position. Check the form."))
    return redirect("dashboard-member-detail", pk=pk)


@login_required
@require_http_methods(["GET", "POST"])
def member_position_edit(request, pk, assignment_pk):
    if not _require(request, "members", "manage_positions"):
        return redirect("dashboard-member-detail", pk=pk)
    member = get_object_or_404(Member, pk=pk)
    assignment = get_object_or_404(
        MemberPositionAssignment.objects.select_related("position"),
        pk=assignment_pk,
        member=member,
    )
    if request.method == "POST":
        form = MemberPositionEditForm(request.POST)
        if form.is_valid():
            try:
                update_assignment(
                    assignment,
                    start_date=form.cleaned_data["start_date"],
                    end_date=form.cleaned_data.get("end_date"),
                    is_primary=bool(form.cleaned_data.get("is_primary")),
                    notes=form.cleaned_data.get("notes") or "",
                    actor=request.user,
                    reason=form.cleaned_data.get("reason") or "",
                )
                messages.success(request, _("Position assignment updated."))
                return redirect("dashboard-member-detail", pk=pk)
            except ValueError as exc:
                messages.error(request, str(exc))
    else:
        form = MemberPositionEditForm(
            initial={
                "start_date": assignment.start_date,
                "end_date": assignment.end_date,
                "is_primary": assignment.is_primary,
                "notes": assignment.notes,
            }
        )
    return render(
        request,
        "dashboard/membership/member_position_edit.html",
        {"form": form, "member": member, "assignment": assignment},
    )


@login_required
@require_POST
def member_position_end(request, pk, assignment_pk):
    if not _require(request, "members", "manage_positions"):
        return redirect("dashboard-member-detail", pk=pk)
    member = get_object_or_404(Member, pk=pk)
    assignment = get_object_or_404(
        MemberPositionAssignment, pk=assignment_pk, member=member
    )
    reason = (request.POST.get("reason") or "").strip()
    try:
        end_position(assignment, actor=request.user, reason=reason)
        messages.success(request, _("Position ended."))
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-member-detail", pk=pk)


@login_required
def member_pdf(request, pk):
    if not _require(request, "members", "profile_download"):
        return redirect("dashboard-member-detail", pk=pk)
    member = get_object_or_404(
        Member.objects.select_related("user", "membership_type").prefetch_related(
            "position_assignments__position"
        ),
        pk=pk,
    )
    include_history = request.GET.get("history") == "1"
    try:
        payload = generate_member_pdf(
            member, actor=request.user, include_history=include_history
        )
    except FileNotFoundError as exc:
        messages.error(request, str(exc))
        return redirect("dashboard-member-detail", pk=pk)
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="member-{member.member_id}.pdf"'
    )
    return response


@login_required
@require_http_methods(["GET", "POST"])
def members_bulk_report(request):
    if not _require(request, "members", "bulk_report"):
        return redirect("dashboard")
    qs = (
        Member.objects.select_related("user", "membership_type")
        .prefetch_related("position_assignments__position")
        .order_by("member_id")
    )
    status = (request.GET.get("status") or request.POST.get("status") or "").strip()
    q = (request.GET.get("q") or request.POST.get("q") or "").strip()
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(member_id__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    if request.method == "POST":
        ids = request.POST.getlist("members")
        selected = list(qs.filter(pk__in=ids)[:200])
        if not selected:
            messages.error(request, _("Select at least one member."))
        else:
            try:
                payload = generate_bulk_members_pdf(selected, actor=request.user)
            except FileNotFoundError as exc:
                messages.error(request, str(exc))
            else:
                response = HttpResponse(payload, content_type="application/pdf")
                response["Content-Disposition"] = (
                    'attachment; filename="members-report.pdf"'
                )
                return response
    return render(
        request,
        "dashboard/membership/members_bulk_report.html",
        {
            "members": qs[:300],
            "status": status,
            "q": q,
            "status_choices": MemberStatus.choices,
        },
    )


@login_required
@require_POST
def member_delete(request, pk):
    if not _require(request, "members", "delete"):
        return redirect("dashboard-members")
    member = get_object_or_404(Member, pk=pk)
    member._audit_user = request.user
    member.delete()
    messages.success(request, _("Member deleted."))
    return redirect("dashboard-members")


@login_required
@require_POST
def member_add_note(request, pk):
    if not _require(request, "members", "edit"):
        return redirect("dashboard-member-detail", pk=pk)
    member = get_object_or_404(Member, pk=pk)
    form = MemberNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.member = member
        note.author = request.user
        note.save()
        messages.success(request, _("Note added."))
    return redirect("dashboard-member-detail", pk=pk)


@login_required
@require_POST
def member_add_document(request, pk):
    if not _require(request, "members", "edit"):
        return redirect("dashboard-member-detail", pk=pk)
    member = get_object_or_404(Member, pk=pk)
    form = MemberDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.member = member
        doc.uploaded_by = request.user
        doc.save()
        messages.success(request, _("Document uploaded."))
    else:
        messages.error(request, _("Could not upload document. Check the file type and size."))
    return redirect("dashboard-member-detail", pk=pk)


def _resolve(name, *args):
    from django.urls import reverse

    return reverse(name, args=args)


# =========================================================================
# Membership Types (generic CRUD)
# =========================================================================

class MembershipTypeList(DashListView):
    model = MembershipType
    permission_module = "membership_types"
    ordering = ["display_order", "name_en"]
    search_fields = ["name_en", "name_bn"]
    page_title = _l("Membership Types")
    page_icon = "bi-card-checklist"
    columns = [
        {"label": _l("Name"), "field": "name_en"},
        {"label": _l("Fee (BDT)"), "field": "fee_amount"},
        {"label": _l("Lifetime"), "field": "is_lifetime"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-membership-type-create"
    edit_url_name = "dashboard-membership-type-edit"
    delete_url_name = "dashboard-membership-type-delete"


class MembershipTypeCreate(DashCreateView):
    model = MembershipType
    permission_module = "membership_types"
    form_class = MembershipTypeForm
    page_title = _l("Add Membership Type")
    success_url_name = "dashboard-membership-types"


class MembershipTypeUpdate(DashUpdateView):
    model = MembershipType
    permission_module = "membership_types"
    form_class = MembershipTypeForm
    page_title = _l("Edit Membership Type")
    success_url_name = "dashboard-membership-types"


class MembershipTypeDelete(DashDeleteView):
    model = MembershipType
    permission_module = "membership_types"
    success_url_name = "dashboard-membership-types"


# =========================================================================
# Member Groups (election eligibility cohorts)
# =========================================================================

class MemberGroupList(DashListView):
    model = MemberGroup
    permission_module = "members"
    ordering = ["name_en"]
    search_fields = ["name_en", "name_bn", "slug"]
    page_title = _l("Member Groups")
    page_icon = "bi-people"
    columns = [
        {"label": _l("Name"), "field": "name_en"},
        {"label": _l("Slug"), "field": "slug"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-member-group-create"
    edit_url_name = "dashboard-member-group-edit"
    delete_url_name = "dashboard-member-group-delete"


class MemberGroupCreate(DashCreateView):
    model = MemberGroup
    permission_module = "members"
    form_class = MemberGroupForm
    page_title = _l("Add Member Group")
    success_url_name = "dashboard-member-groups"


class MemberGroupUpdate(DashUpdateView):
    model = MemberGroup
    permission_module = "members"
    form_class = MemberGroupForm
    page_title = _l("Edit Member Group")
    success_url_name = "dashboard-member-groups"


class MemberGroupDelete(DashDeleteView):
    model = MemberGroup
    permission_module = "members"
    success_url_name = "dashboard-member-groups"


# =========================================================================
# Applications workspace
# =========================================================================

@login_required
def applications_list(request):
    if not _require(request, "applications", "view"):
        return redirect("dashboard")
    status = request.GET.get("status", ApplicationStatus.PENDING)
    qs = MemberApplication.objects.order_by("-created_at")
    if status in dict(ApplicationStatus.choices):
        qs = qs.filter(status=status)

    counts = {
        code: MemberApplication.objects.filter(status=code).count()
        for code, _label in ApplicationStatus.choices
    }

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/membership/applications_list.html",
        {
            "page_obj": page_obj,
            "applications": page_obj.object_list,
            "status": status,
            "status_choices": ApplicationStatus.choices,
            "counts": counts,
            "can_approve": _require(request, "applications", "approve"),
            "can_reject": _require(request, "applications", "reject"),
            "can_review": _require(request, "applications", "review"),
        },
    )


@login_required
def application_detail(request, pk):
    if not _require(request, "applications", "view"):
        return redirect("dashboard")
    application = get_object_or_404(
        MemberApplication.objects.prefetch_related("document_requests", "events"),
        pk=pk,
    )
    can_view_sensitive = _can_view_sensitive_history(request.user)
    history_qs = _edit_history_qs("MemberApplication", application.pk)
    history_page = Paginator(history_qs, 15).get_page(request.GET.get("history_page"))
    edit_history = []
    for log in history_page:
        old, new = _redact_history_values(
            log,
            can_view_sensitive=can_view_sensitive,
            sensitive_fields=SENSITIVE_APPLICATION_FIELDS,
        )
        changes = [
            {"field": key, "old": old.get(key), "new": new.get(key)}
            for key in sorted(set(old) | set(new))
        ]
        edit_history.append({"log": log, "changes": changes})
    return render(
        request,
        "dashboard/membership/application_detail.html",
        {
            "application": application,
            "document_requests": application.document_requests.all(),
            "events": application.events.select_related("actor")[:50],
            "edit_history": edit_history,
            "edit_history_page": history_page,
            "can_approve": _require(request, "applications", "approve"),
            "can_reject": _require(request, "applications", "reject"),
            "can_review": _require(request, "applications", "review"),
            "can_edit": _require(request, "applications", "edit")
            or _require(request, "applications", "review"),
            "can_download": _require(request, "applications", "download"),
            "can_view_sensitive_history": can_view_sensitive,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def application_edit(request, pk):
    if not (
        _require(request, "applications", "edit")
        or _require(request, "applications", "review")
        or _require(request, "applications", "edit_sensitive")
    ):
        return redirect("dashboard-applications")
    application = get_object_or_404(MemberApplication, pk=pk)
    can_edit_sensitive = _require(request, "applications", "edit_sensitive")
    if request.method == "POST":
        form = ApplicationEditForm(request.POST, instance=application)
        if form.is_valid():
            cleaned = {
                k: form.cleaned_data[k]
                for k in form.Meta.fields
                if k in form.cleaned_data
            }
            diffs = compute_field_diffs(application, cleaned, cleaned.keys())
            sensitive = requires_reason(diffs, SENSITIVE_APPLICATION_FIELDS)
            if sensitive and not can_edit_sensitive:
                messages.error(
                    request,
                    _("You do not have permission to change sensitive official fields."),
                )
            else:
                try:
                    apply_model_edits(
                        application,
                        cleaned,
                        actor=request.user,
                        entity="MemberApplication",
                        reason=form.cleaned_data.get("reason") or "",
                        sensitive_fields=SENSITIVE_APPLICATION_FIELDS,
                        fields=cleaned.keys(),
                        request=request,
                    )
                    messages.success(request, _("Application updated."))
                    return redirect("dashboard-application-detail", pk=application.pk)
                except ValueError as exc:
                    messages.error(request, str(exc))
    else:
        form = ApplicationEditForm(instance=application)
    return render(
        request,
        "dashboard/membership/application_edit.html",
        {
            "form": form,
            "application": application,
            "can_edit_sensitive": can_edit_sensitive,
            "sensitive_fields": sorted(SENSITIVE_APPLICATION_FIELDS),
        },
    )


@login_required
def application_pdf(request, pk):
    if not _require(request, "applications", "download"):
        return redirect("dashboard-application-detail", pk=pk)
    application = get_object_or_404(MemberApplication, pk=pk)
    try:
        payload = generate_application_pdf(application, actor=request.user)
    except FileNotFoundError as exc:
        messages.error(request, str(exc))
        return redirect("dashboard-application-detail", pk=pk)
    ref = application.reference_code or str(application.pk)[:8]
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="application-{ref}.pdf"'
    return response


@login_required
@require_http_methods(["GET", "POST"])
def applications_bulk_report(request):
    if not _require(request, "applications", "bulk_report"):
        return redirect("dashboard")
    qs = MemberApplication.objects.order_by("-created_at")
    status = (request.GET.get("status") or request.POST.get("status") or "").strip()
    q = (request.GET.get("q") or request.POST.get("q") or "").strip()
    if status in dict(ApplicationStatus.choices):
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(reference_code__icontains=q)
            | Q(english_name__icontains=q)
            | Q(bangla_name__icontains=q)
            | Q(phone__icontains=q)
        )
    if request.method == "POST":
        ids = request.POST.getlist("applications")
        selected = list(qs.filter(pk__in=ids)[:200])
        if not selected:
            messages.error(request, _("Select at least one application."))
        else:
            try:
                payload = generate_bulk_applications_pdf(selected, actor=request.user)
            except FileNotFoundError as exc:
                messages.error(request, str(exc))
            else:
                response = HttpResponse(payload, content_type="application/pdf")
                response["Content-Disposition"] = (
                    'attachment; filename="applications-report.pdf"'
                )
                return response
    return render(
        request,
        "dashboard/membership/applications_bulk_report.html",
        {
            "applications": qs[:300],
            "status": status,
            "q": q,
            "status_choices": ApplicationStatus.choices,
        },
    )


@login_required
@require_POST
def application_action(request, pk):
    application = get_object_or_404(MemberApplication, pk=pk)
    action = request.POST.get("action")
    application._audit_user = request.user

    if action == "approve":
        if not _require(request, "applications", "approve"):
            return redirect("dashboard-applications")
        try:
            member = transition_application(
                application, ApplicationStatus.APPROVED, request.user
            )
            messages.success(
                request,
                _("Application approved. Member %(id)s created.") % {"id": member.member_id},
            )
        except (TransitionError, ValueError) as exc:
            messages.error(request, str(exc))
    elif action == "reject":
        if not _require(request, "applications", "reject"):
            return redirect("dashboard-applications")
        reason = request.POST.get("reason", "")
        try:
            transition_application(
                application,
                ApplicationStatus.REJECTED,
                request.user,
                reason=reason,
                admin_message=reason,
            )
            messages.success(request, _("Application rejected."))
        except (TransitionError, ValueError) as exc:
            messages.error(request, str(exc))
    elif action == "review":
        if not _require(request, "applications", "review"):
            return redirect("dashboard-applications")
        try:
            transition_application(
                application, ApplicationStatus.UNDER_REVIEW, request.user
            )
            messages.success(request, _("Application marked as under review."))
        except (TransitionError, ValueError) as exc:
            messages.error(request, str(exc))
    elif action == "request_documents":
        if not _require(request, "applications", "review"):
            return redirect("dashboard-applications")
        label = (request.POST.get("document_label") or "").strip()
        instruction = (request.POST.get("instruction") or "").strip()
        admin_message = (request.POST.get("admin_message") or "").strip()
        if not label:
            messages.error(request, _("Document label is required."))
        else:
            if application.status == ApplicationStatus.PENDING:
                try:
                    transition_application(
                        application, ApplicationStatus.UNDER_REVIEW, request.user
                    )
                except (TransitionError, ValueError):
                    pass
            request_missing_documents(
                application,
                request.user,
                [{"label": label, "instruction": instruction}],
                admin_message=admin_message,
            )
            messages.success(request, _("Missing document requested from applicant."))

    return redirect(request.META.get("HTTP_REFERER") or "dashboard-applications")


# =========================================================================
# Membership Fees
# =========================================================================

def _fee_return_url(request, member):
    """Prefer fee detail when the action originated there."""
    nxt = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if nxt.startswith("/dashboard/membership-fees/"):
        return nxt
    referer = request.META.get("HTTP_REFERER") or ""
    if f"/dashboard/membership-fees/{member.pk}" in referer:
        return "dashboard-membership-fee-detail"
    return None


@login_required
def fees_settings(request):
    """Configure monthly fee, registration fee, and fee starting month."""
    if not _require(request, "membership_fees", "edit"):
        if not _require(request, "membership_fees", "view"):
            return redirect("dashboard")
        settings_obj = MembershipFeeSettings.load()
        return render(
            request,
            "dashboard/membership/fees_settings.html",
            {
                "form": MembershipFeeSettingsForm(instance=settings_obj),
                "fee_settings": settings_obj,
                "can_edit": False,
            },
        )
    settings_obj = MembershipFeeSettings.load()
    if request.method == "POST":
        form = MembershipFeeSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("Membership fee settings saved."))
            return redirect("dashboard-membership-fees-settings")
    else:
        form = MembershipFeeSettingsForm(instance=settings_obj)
    return render(
        request,
        "dashboard/membership/fees_settings.html",
        {
            "form": form,
            "fee_settings": settings_obj,
            "can_edit": True,
        },
    )


@login_required
def fees_list(request):
    """One row per member with aggregated fee summary (not one row per month)."""
    if not _require(request, "membership_fees", "view"):
        return redirect("dashboard")
    qs = Member.objects.select_related("user", "membership_type").order_by(
        "first_name", "last_name", "member_id"
    )
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    pending_only = request.GET.get("pending", "").strip() in {"1", "true", "yes"}
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.filter(status=MemberStatus.APPROVED)
    if q:
        qs = qs.filter(
            Q(member_id__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(user__email__icontains=q)
        )
    qs = annotate_members_for_fee_list(qs)
    if pending_only:
        qs = qs.filter(pending_months_count__gt=0)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    members = list(page_obj.object_list)
    summaries = summaries_for_members(members)
    rows = [{"member": m, "summary": summaries[m.pk]} for m in members]
    fee_settings = MembershipFeeSettings.load()

    return render(
        request,
        "dashboard/membership/fees_list.html",
        {
            "page_obj": page_obj,
            "rows": rows,
            "q": q,
            "status": status,
            "pending_only": pending_only,
            "status_choices": MemberStatus.choices,
            "monthly_fee": get_monthly_fee_amount(),
            "fee_settings": fee_settings,
            "can_create": _require(request, "membership_fees", "create"),
            "can_edit_settings": _require(request, "membership_fees", "edit"),
        },
    )


@login_required
def fees_detail(request, pk):
    """Per-member fee profile for finance/admin (RBAC: membership_fees.view)."""
    if not _require(request, "membership_fees", "view"):
        return redirect("dashboard")
    member = get_object_or_404(
        Member.objects.select_related("user", "membership_type"), pk=pk
    )
    summary = summarize_member_fees(member, ensure_ledger=True)
    fees = member.membership_fees.select_related("fee_payment").order_by("-year", "-month")
    payments = MembershipFeePayment.objects.filter(member=member).order_by("-created_at")[:30]
    events = MembershipBillingEvent.objects.filter(member=member).order_by("-created_at")[:40]
    autopay = get_or_create_autopay(member)
    try:
        registration_fee = member.registration_fee
    except MembershipRegistrationFee.DoesNotExist:
        registration_fee = None
    return render(
        request,
        "dashboard/membership/fees_detail.html",
        {
            "member": member,
            "fee_summary": summary,
            "fees": fees,
            "payments": payments,
            "billing_events": events,
            "autopay": autopay,
            "registration_fee": registration_fee,
            "monthly_fee": get_monthly_fee_amount(),
            "offline_methods": [
                (m.value, m.label)
                for m in PaymentMethod
                if m != PaymentMethod.SSLCOMMERZ
            ],
            "can_record_fee": _require(request, "membership_fees", "create"),
            "can_manage_autopay": _require(request, "membership_fees", "edit"),
            "can_view_member": _require(request, "members", "view"),
        },
    )


@login_required
@require_POST
def fee_record_registration(request, pk):
    if not _require(request, "membership_fees", "create"):
        return redirect("dashboard-membership-fees")
    member = get_object_or_404(Member, pk=pk)
    method = request.POST.get("payment_method") or PaymentMethod.CASH
    notes = (request.POST.get("notes") or "").strip()
    transaction_id = (request.POST.get("transaction_id") or "").strip()
    if method == PaymentMethod.SSLCOMMERZ:
        messages.error(request, _("Use offline methods for manual recording."))
        return redirect("dashboard-membership-fee-detail", pk=member.pk)
    try:
        record_admin_registration_fee_payment(
            member,
            payment_method=method,
            actor=request.user,
            notes=notes,
            transaction_id=transaction_id,
        )
        messages.success(request, _("Registration fee payment recorded."))
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-membership-fee-detail", pk=member.pk)


@login_required
@require_POST
def fee_record_payment(request, pk):
    if not _require(request, "membership_fees", "create"):
        return redirect("dashboard-members")
    member = get_object_or_404(Member, pk=pk)
    selected = request.POST.getlist("months")
    method = request.POST.get("payment_method") or PaymentMethod.CASH
    notes = (request.POST.get("notes") or "").strip()
    transaction_id = (request.POST.get("transaction_id") or "").strip()
    months = []
    for raw in selected:
        try:
            y_str, m_str = raw.split("-", 1)
            months.append({"year": int(y_str), "month": int(m_str)})
        except (TypeError, ValueError):
            continue
    dest = _fee_return_url(request, member)
    if method == PaymentMethod.SSLCOMMERZ:
        messages.error(request, _("Use offline methods for manual recording."))
        if dest == "dashboard-membership-fee-detail":
            return redirect(dest, pk=member.pk)
        if isinstance(dest, str) and dest.startswith("/"):
            return redirect(dest)
        return redirect("dashboard-member-detail", pk=member.pk)
    if not months:
        messages.error(request, _("Select at least one month."))
        if dest == "dashboard-membership-fee-detail":
            return redirect(dest, pk=member.pk)
        if isinstance(dest, str) and dest.startswith("/"):
            return redirect(dest)
        return redirect("dashboard-member-detail", pk=member.pk)
    try:
        record_admin_fee_payment(
            member,
            months,
            payment_method=method,
            actor=request.user,
            notes=notes,
            transaction_id=transaction_id,
        )
        messages.success(request, _("Membership fee payment recorded."))
    except Exception as exc:
        messages.error(request, str(exc))
    if dest == "dashboard-membership-fee-detail":
        return redirect(dest, pk=member.pk)
    if isinstance(dest, str) and dest.startswith("/"):
        return redirect(dest)
    return redirect("dashboard-member-detail", pk=member.pk)


@login_required
@require_POST
def fee_deactivate_autopay(request, pk):
    if not _require(request, "membership_fees", "edit"):
        return redirect("dashboard-members")
    member = get_object_or_404(Member, pk=pk)
    # Admin/Finance may deactivate only — never silently enable.
    deactivate_autopay(member, actor=request.user, reason="Deactivated by admin/finance")
    messages.success(request, _("Auto-payment deactivated for this member."))
    dest = _fee_return_url(request, member)
    if dest == "dashboard-membership-fee-detail":
        return redirect(dest, pk=member.pk)
    if isinstance(dest, str) and dest.startswith("/"):
        return redirect(dest)
    return redirect("dashboard-member-detail", pk=member.pk)
