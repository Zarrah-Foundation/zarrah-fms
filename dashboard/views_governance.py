"""Dashboard governance views — meetings, resolutions, member portals."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from dashboard.forms_governance import (
    AddParticipantGroupForm,
    AddParticipantMemberForm,
    AgendaItemForm,
    GuestForm,
    MeetingForm,
    MeetingRsvpForm,
    MeetingTypeForm,
    MemberSignatureForm,
    NewVersionForm,
    ProceedingsForm,
    PublicShareAdminForm,
    ResolutionForm,
    ResolutionSignForm,
    SignerSelectForm,
)
from governance.documents import resolution_file_response
from governance.models import (
    Meeting,
    MeetingGuest,
    MeetingParticipant,
    MeetingStatus,
    Resolution,
    ResolutionSigner,
    ResolutionStatus,
)
from governance.notifications import notify_meeting_invitation
from governance.sequences import generate_meeting_reference
from governance.services.agenda import add_agenda_item, reorder_agenda, save_proceedings
from governance.services.guests import add_guest, delete_guest, update_guest
from governance.services.lifecycle import ALLOWED_TRANSITIONS, transition_meeting
from governance.services.participants import (
    add_participants_from_group,
    add_participants_from_members,
    freeze_eligible_roster,
    freeze_participants,
    mark_attendance,
    present_participants_qs,
    set_participant_response,
)
from governance.services.public_share import (
    enable_public_share,
    revoke_public_share,
    set_share_password,
)
from governance.services.quorum import quorum_snapshot
from governance.services.resolutions import (
    create_new_version,
    create_resolution,
    finalize_resolution,
    prepare_for_signing,
    select_signers,
    sign_resolution,
    update_draft_resolution,
)
from members.models import Member, MemberPositionAssignment
from members.positions import format_position_label, primary_assignment
from rbac.permissions import has_action

def _deny():
    return redirect("dashboard")


def _require(user, module: str, action: str) -> bool:
    return has_action(user, module, action)


def _member_profile(user):
    return getattr(user, "member_profile", None)


def _get_participant_for_user(meeting: Meeting, user) -> MeetingParticipant | None:
    member = _member_profile(user)
    if member is None:
        return None
    return (
        MeetingParticipant.objects.filter(meeting=meeting, member=member)
        .select_related("member")
        .first()
    )


# ---------------------------------------------------------------------------
# Admin — meeting types
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def meeting_types_list(request):
    if not _require(request.user, "meetings", "manage"):
        return _deny()
    from governance.models import MeetingType

    types = MeetingType.objects.annotate(meeting_count=Count("meetings")).order_by(
        "display_order", "name_en"
    )
    return render(
        request,
        "dashboard/governance/meeting_types_list.html",
        {"types": types, "can_manage": True},
    )


@login_required
@require_http_methods(["GET", "POST"])
def meeting_type_create(request):
    if not _require(request.user, "meetings", "manage"):
        return _deny()
    form = MeetingTypeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Meeting type created."))
        return redirect("dashboard-meeting-types")
    return render(
        request,
        "dashboard/governance/meeting_type_form.html",
        {"form": form, "is_create": True},
    )


@login_required
@require_http_methods(["GET", "POST"])
def meeting_type_edit(request, pk):
    if not _require(request.user, "meetings", "manage"):
        return _deny()
    from governance.models import MeetingType

    mt = get_object_or_404(MeetingType, pk=pk)
    form = MeetingTypeForm(request.POST or None, instance=mt)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Meeting type updated."))
        return redirect("dashboard-meeting-types")
    return render(
        request,
        "dashboard/governance/meeting_type_form.html",
        {"form": form, "is_create": False, "meeting_type": mt},
    )


# ---------------------------------------------------------------------------
# Admin — meetings
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def meetings_list(request):
    if not _require(request.user, "meetings", "view"):
        return _deny()

    qs = Meeting.objects.select_related("meeting_type").annotate(
        participant_count=Count("participants", distinct=True)
    )
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    if q:
        qs = qs.filter(
            Q(reference_id__icontains=q)
            | Q(title_bn__icontains=q)
            | Q(title_en__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    page_obj = Paginator(qs.order_by("-starts_at", "-created_at"), 25).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "dashboard/governance/meetings_list.html",
        {
            "meetings": page_obj,
            "page_obj": page_obj,
            "search_query": q,
            "status_filter": status,
            "status_choices": MeetingStatus.choices,
            "can_create": _require(request.user, "meetings", "create"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def meeting_create(request):
    if not _require(request.user, "meetings", "create"):
        return _deny()
    form = MeetingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        meeting = form.save(commit=False)
        meeting.reference_id = generate_meeting_reference()
        meeting.created_by = request.user
        meeting.status = MeetingStatus.DRAFT
        meeting.save()
        messages.success(request, _("Meeting created."))
        return redirect("dashboard-meeting-detail", pk=meeting.pk)
    return render(
        request,
        "dashboard/governance/meeting_form.html",
        {"form": form, "is_create": True, "meeting": None},
    )


@login_required
@require_http_methods(["GET", "POST"])
def meeting_edit(request, pk):
    if not _require(request.user, "meetings", "edit"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    if meeting.status in {MeetingStatus.FINALIZED, MeetingStatus.ARCHIVED}:
        messages.error(request, _("Finalized meetings cannot be edited."))
        return redirect("dashboard-meeting-detail", pk=pk)
    form = MeetingForm(request.POST or None, instance=meeting)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Meeting updated."))
        return redirect("dashboard-meeting-detail", pk=pk)
    return render(
        request,
        "dashboard/governance/meeting_form.html",
        {"form": form, "is_create": False, "meeting": meeting},
    )


@login_required
@require_http_methods(["GET"])
def meeting_detail(request, pk):
    if not _require(request.user, "meetings", "view"):
        return _deny()
    meeting = get_object_or_404(
        Meeting.objects.select_related("meeting_type", "proceeding"),
        pk=pk,
    )
    participants = list(
        meeting.participants.select_related("member")
        .prefetch_related(
            Prefetch(
                "member__position_assignments",
                queryset=MemberPositionAssignment.objects.filter(
                    is_active=True
                ).select_related("position"),
            )
        )
        .order_by("member__member_id")
    )
    for participant in participants:
        assignment = primary_assignment(participant.member)
        participant.position_label = format_position_label(assignment) or "—"
    guests = meeting.guests.order_by("full_name")
    agenda_items = meeting.agenda_items.all()
    resolutions = meeting.resolutions.order_by("-created_at")
    proceeding = getattr(meeting, "proceeding", None)
    quorum = quorum_snapshot(meeting)
    mt = meeting.meeting_type
    quorum_rule = f"{mt.quorum_numerator}/{mt.quorum_denominator}"
    allowed_next = sorted(ALLOWED_TRANSITIONS.get(meeting.status, set()))

    proceeding_form = None
    if _require(request.user, "meetings", "manage_agenda"):
        if proceeding is not None:
            proceeding_form = ProceedingsForm(instance=proceeding)
        else:
            proceeding_form = ProceedingsForm()

    return render(
        request,
        "dashboard/governance/meeting_detail.html",
        {
            "meeting": meeting,
            "participants": participants,
            "guests": guests,
            "agenda_items": agenda_items,
            "resolutions": resolutions,
            "proceeding": proceeding,
            "quorum": quorum,
            "quorum_rule": quorum_rule,
            "allowed_next": allowed_next,
            "show_online": True,
            "can_edit": _require(request.user, "meetings", "edit")
            and meeting.status
            not in {MeetingStatus.FINALIZED, MeetingStatus.ARCHIVED},
            "can_create_resolution": _require(request.user, "resolutions", "create"),
            "can_manage_participants": _require(
                request.user, "meetings", "manage_participants"
            ),
            "can_manage_attendance": _require(
                request.user, "meetings", "manage_attendance"
            ),
            "can_manage_agenda": _require(request.user, "meetings", "manage_agenda"),
            "add_member_form": AddParticipantMemberForm(),
            "add_group_form": AddParticipantGroupForm(),
            "guest_form": GuestForm(),
            "agenda_form": AgendaItemForm(),
            "proceeding_form": proceeding_form,
        },
    )


@login_required
@require_POST
def meeting_transition(request, pk):
    if not (
        _require(request.user, "meetings", "edit")
        or _require(request.user, "meetings", "manage")
        or _require(request.user, "meetings", "finalize")
    ):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    action = (request.POST.get("action") or "").strip()
    new_status = (request.POST.get("new_status") or "").strip()

    try:
        if action == "send_invitations":
            freeze_eligible_roster(meeting, actor=request.user)
            freeze_participants(meeting)
            if meeting.status == MeetingStatus.DRAFT:
                transition_meeting(
                    meeting, MeetingStatus.SCHEDULED, actor=request.user
                )
            meeting.refresh_from_db()
            if meeting.status == MeetingStatus.SCHEDULED:
                transition_meeting(
                    meeting, MeetingStatus.INVITATIONS_SENT, actor=request.user
                )
            meeting.refresh_from_db()
            for participant in meeting.participants.select_related("member__user"):
                notify_meeting_invitation(meeting, participant)
            messages.success(request, _("Invitations sent."))
        elif new_status:
            if new_status == MeetingStatus.FINALIZED and not _require(
                request.user, "meetings", "finalize"
            ):
                messages.error(request, _("You cannot finalize meetings."))
                return redirect("dashboard-meeting-detail", pk=pk)
            transition_meeting(meeting, new_status, actor=request.user)
            messages.success(request, _("Meeting status updated."))
        else:
            messages.error(request, _("No transition specified."))
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_participants_freeze(request, pk):
    if not _require(request.user, "meetings", "manage_participants"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    freeze_eligible_roster(meeting, actor=request.user)
    freeze_participants(meeting)
    messages.success(request, _("Participant roster frozen."))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_participant_add_member(request, pk):
    if not _require(request.user, "meetings", "manage_participants"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    form = AddParticipantMemberForm(request.POST)
    if form.is_valid():
        try:
            add_participants_from_members(
                meeting, [form.cleaned_data["member"]], actor=request.user
            )
            messages.success(request, _("Participant added."))
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, _("Could not add participant."))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_participant_add_group(request, pk):
    if not _require(request.user, "meetings", "manage_participants"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    form = AddParticipantGroupForm(request.POST)
    if form.is_valid():
        try:
            created = add_participants_from_group(
                meeting, form.cleaned_data["group"], actor=request.user
            )
            messages.success(
                request, _("Added %(n)s participant(s) from group.") % {"n": len(created)}
            )
        except ValueError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, _("Could not add group."))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_attendance_mark(request, pk, participant_pk):
    if not _require(request.user, "meetings", "manage_attendance"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    participant = get_object_or_404(
        MeetingParticipant, pk=participant_pk, meeting=meeting
    )
    status = (request.POST.get("status") or "").strip()
    try:
        mark_attendance(participant, status, actor=request.user)
        messages.success(request, _("Attendance recorded."))
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_guest_add(request, pk):
    if not _require(request.user, "meetings", "manage_participants"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    form = GuestForm(request.POST)
    if form.is_valid():
        add_guest(meeting, actor=request.user, **form.cleaned_data)
        messages.success(request, _("Guest added."))
    else:
        messages.error(request, _("Could not add guest."))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_http_methods(["GET", "POST"])
def meeting_guest_edit(request, pk, guest_pk):
    if not _require(request.user, "meetings", "manage_participants"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    guest = get_object_or_404(MeetingGuest, pk=guest_pk, meeting=meeting)
    form = GuestForm(request.POST or None, instance=guest)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        update_guest(
            guest,
            actor=request.user,
            full_name=data["full_name"],
            organization=data.get("organization") or "",
            designation=data.get("designation") or "",
            email=data.get("email") or "",
            phone=data.get("phone") or "",
            notes=data.get("notes") or "",
        )
        from governance.services.guests import set_guest_status

        set_guest_status(guest, data["status"], actor=request.user)
        messages.success(request, _("Guest updated."))
        return redirect("dashboard-meeting-detail", pk=pk)
    return render(
        request,
        "dashboard/governance/guest_form.html",
        {"form": form, "meeting": meeting, "guest": guest},
    )


@login_required
@require_POST
def meeting_guest_delete(request, pk, guest_pk):
    if not _require(request.user, "meetings", "manage_participants"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    guest = get_object_or_404(MeetingGuest, pk=guest_pk, meeting=meeting)
    delete_guest(guest, actor=request.user)
    messages.success(request, _("Guest removed."))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_agenda_add(request, pk):
    if not _require(request.user, "meetings", "manage_agenda"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    form = AgendaItemForm(request.POST, request.FILES)
    if form.is_valid():
        add_agenda_item(
            meeting,
            actor=request.user,
            supporting_document=form.cleaned_data.get("supporting_document"),
            **{
                k: form.cleaned_data[k]
                for k in (
                    "title_bn",
                    "title_en",
                    "description_bn",
                    "description_en",
                    "presenter_name",
                )
            },
        )
        messages.success(request, _("Agenda item added."))
    else:
        messages.error(request, _("Could not add agenda item."))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_agenda_reorder(request, pk):
    if not _require(request.user, "meetings", "manage_agenda"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    raw = (request.POST.get("order") or "").strip()
    ids = [x for x in raw.split(",") if x]
    try:
        reorder_agenda(meeting, ids, actor=request.user)
        messages.success(request, _("Agenda order saved."))
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-meeting-detail", pk=pk)


@login_required
@require_POST
def meeting_proceedings_save(request, pk):
    if not _require(request.user, "meetings", "manage_agenda"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=pk)
    form = ProceedingsForm(request.POST)
    if form.is_valid():
        save_proceedings(
            meeting,
            content_bn=form.cleaned_data.get("content_bn") or "",
            content_en=form.cleaned_data.get("content_en") or "",
            actor=request.user,
        )
        messages.success(request, _("Proceedings saved."))
    else:
        messages.error(request, _("Could not save proceedings."))
    return redirect("dashboard-meeting-detail", pk=pk)


# ---------------------------------------------------------------------------
# Admin — resolutions
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def resolution_create(request, meeting_pk):
    if not _require(request.user, "resolutions", "create"):
        return _deny()
    meeting = get_object_or_404(Meeting, pk=meeting_pk)
    form = ResolutionForm(request.POST or None, meeting=meeting)
    if request.method == "POST" and form.is_valid():
        try:
            resolution = create_resolution(
                meeting,
                title_bn=form.cleaned_data["title_bn"],
                title_en=form.cleaned_data.get("title_en") or "",
                content_bn=form.cleaned_data["content_bn"],
                content_en=form.cleaned_data.get("content_en") or "",
                decision_bn=form.cleaned_data.get("decision_bn") or "",
                decision_en=form.cleaned_data.get("decision_en") or "",
                agenda_item=form.cleaned_data.get("agenda_item"),
                actor=request.user,
            )
            messages.success(request, _("Resolution created."))
            return redirect("dashboard-resolution-detail", pk=resolution.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
    return render(
        request,
        "dashboard/governance/resolution_form.html",
        {"form": form, "meeting": meeting, "is_create": True, "resolution": None},
    )


@login_required
@require_http_methods(["GET", "POST"])
def resolution_detail(request, pk):
    if not _require(request.user, "resolutions", "view"):
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related(
            "meeting", "current_version", "public_share", "agenda_item"
        ),
        pk=pk,
    )
    version = resolution.current_version
    signers = (
        ResolutionSigner.objects.filter(version=version).select_related("member")
        if version
        else []
    )
    present = list(
        present_participants_qs(resolution.meeting)
        .select_related("member")
        .prefetch_related(
            Prefetch(
                "member__position_assignments",
                queryset=MemberPositionAssignment.objects.filter(
                    is_active=True
                ).select_related("position"),
            )
        )
    )
    selected_ids = {
        str(s.member_id) for s in signers if getattr(s, "is_required", True)
    }
    present_signers = []
    for p in present:
        assignment = primary_assignment(p.member)
        mid = str(p.member_id)
        present_signers.append(
            {
                "member_id": mid,
                "member_code": p.member.member_id,
                "name": f"{p.member.first_name} {p.member.last_name}".strip()
                or p.member.member_id,
                "position_label": format_position_label(assignment) or "—",
                "council": (
                    assignment.position.get_council_body_display() if assignment else ""
                ),
                "selected": mid in selected_ids,
            }
        )
    signer_choices = [
        (row["member_id"], f"{row['member_code']} — {row['name']}")
        for row in present_signers
    ]

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        try:
            if action == "prepare" and _require(request.user, "resolutions", "manage"):
                prepare_for_signing(resolution, actor=request.user)
                messages.success(request, _("Resolution prepared for signing."))
            elif action == "select_signers" and _require(
                request.user, "resolutions", "manage_signers"
            ):
                form = SignerSelectForm(request.POST, choices=signer_choices)
                if form.is_valid():
                    select_signers(
                        resolution,
                        form.cleaned_data["members"],
                        actor=request.user,
                    )
                    messages.success(request, _("Signers selected."))
                else:
                    messages.error(request, _("Select at least one present member."))
            elif action == "finalize" and _require(
                request.user, "resolutions", "finalize"
            ):
                finalize_resolution(resolution, actor=request.user)
                messages.success(request, _("Resolution finalized."))
            elif action == "new_version" and _require(
                request.user, "resolutions", "edit"
            ):
                vform = NewVersionForm(request.POST)
                if vform.is_valid():
                    kwargs = {"reason": vform.cleaned_data["reason"]}
                    if vform.cleaned_data.get("content_bn"):
                        kwargs["content_bn"] = vform.cleaned_data["content_bn"]
                    if vform.cleaned_data.get("content_en"):
                        kwargs["content_en"] = vform.cleaned_data["content_en"]
                    create_new_version(resolution, actor=request.user, **kwargs)
                    messages.success(request, _("New version created."))
                else:
                    messages.error(request, _("Provide a revision reason."))
            elif action == "enable_share" and _require(
                request.user, "resolution_public_sharing", "manage"
            ):
                sform = PublicShareAdminForm(request.POST)
                if sform.is_valid():
                    password = sform.cleaned_data.get("password") or None
                    if sform.cleaned_data.get("clear_password"):
                        password = None
                    share = enable_public_share(
                        resolution,
                        actor=request.user,
                        password=password if password else None,
                        expires_at=sform.cleaned_data.get("expires_at"),
                        show_signer_details=sform.cleaned_data.get(
                            "show_signer_details", True
                        ),
                    )
                    if sform.cleaned_data.get("clear_password"):
                        set_share_password(resolution, None, actor=request.user)
                    elif password:
                        set_share_password(resolution, password, actor=request.user)
                    messages.success(
                        request,
                        _("Public sharing enabled. Token: %(t)s") % {"t": share.token},
                    )
                else:
                    messages.error(request, _("Invalid share settings."))
            elif action == "revoke_share" and _require(
                request.user, "resolution_public_sharing", "manage"
            ):
                revoke_public_share(resolution, actor=request.user)
                messages.success(request, _("Public sharing revoked."))
            elif action == "update_draft" and _require(
                request.user, "resolutions", "edit"
            ):
                rform = ResolutionForm(request.POST, meeting=resolution.meeting)
                if rform.is_valid():
                    update_draft_resolution(
                        resolution,
                        title_bn=rform.cleaned_data["title_bn"],
                        title_en=rform.cleaned_data.get("title_en") or "",
                        content_bn=rform.cleaned_data["content_bn"],
                        content_en=rform.cleaned_data.get("content_en") or "",
                        decision_bn=rform.cleaned_data.get("decision_bn") or "",
                        decision_en=rform.cleaned_data.get("decision_en") or "",
                        actor=request.user,
                    )
                    messages.success(request, _("Draft updated."))
                else:
                    messages.error(request, _("Could not update draft."))
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dashboard-resolution-detail", pk=pk)

    share = getattr(resolution, "public_share", None)
    signer_list = list(signers) if signers is not None else []
    signed_count = sum(1 for s in signer_list if s.signed_at)
    required_count = sum(1 for s in signer_list if s.is_required)
    return render(
        request,
        "dashboard/governance/resolution_detail.html",
        {
            "resolution": resolution,
            "version": version,
            "signers": signer_list,
            "signed_count": signed_count,
            "required_signer_count": required_count,
            "remaining_signers": max(required_count - signed_count, 0),
            "versions": resolution.versions.order_by("-version_number"),
            "signer_form": SignerSelectForm(choices=signer_choices),
            "present_signers": present_signers,
            "share_form": PublicShareAdminForm(
                initial={
                    "show_signer_details": getattr(share, "show_signer_details", True),
                    "expires_at": getattr(share, "expires_at", None),
                }
            ),
            "new_version_form": NewVersionForm(),
            "share": share,
            "can_manage": _require(request.user, "resolutions", "manage"),
            "can_manage_signers": _require(
                request.user, "resolutions", "manage_signers"
            ),
            "can_finalize": _require(request.user, "resolutions", "finalize"),
            "can_edit": _require(request.user, "resolutions", "edit"),
            "can_share": _require(
                request.user, "resolution_public_sharing", "manage"
            ),
            "can_download": _require(
                request.user, "resolution_documents", "download"
            ),
        },
    )


@login_required
@require_http_methods(["GET"])
def resolution_document_pdf(request, pk):
    if not _require(request.user, "resolution_documents", "download"):
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related("current_version", "meeting"),
        pk=pk,
    )
    return resolution_file_response(resolution, fmt="pdf", actor=request.user)


@login_required
@require_http_methods(["GET"])
def resolution_document_docx(request, pk):
    if not _require(request.user, "resolution_documents", "download"):
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related("current_version", "meeting"),
        pk=pk,
    )
    return resolution_file_response(resolution, fmt="docx", actor=request.user)


# ---------------------------------------------------------------------------
# Member portal
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET"])
def my_meetings(request):
    member = _member_profile(request.user)
    if member is None:
        messages.info(request, _("No member profile is linked to this account."))
        return _deny()
    now = timezone.now()
    qs = (
        MeetingParticipant.objects.filter(member=member)
        .select_related("meeting", "meeting__meeting_type")
        .order_by("-meeting__starts_at")
    )
    upcoming = [p for p in qs if p.meeting.starts_at >= now]
    past = [p for p in qs if p.meeting.starts_at < now]
    return render(
        request,
        "dashboard/governance/my_meetings.html",
        {"upcoming": upcoming, "past": past},
    )


@login_required
@require_http_methods(["GET", "POST"])
def my_meeting_detail(request, pk):
    member = _member_profile(request.user)
    if member is None:
        return _deny()
    meeting = get_object_or_404(Meeting.objects.select_related("meeting_type"), pk=pk)
    participant = _get_participant_for_user(meeting, request.user)
    if participant is None:
        # IDOR: not invited to this meeting
        messages.error(request, _("You are not a participant in this meeting."))
        return redirect("my-meetings")

    rsvp_form = None
    if participant.status == "INVITED":
        rsvp_form = MeetingRsvpForm(request.POST or None)
        if request.method == "POST":
            # Support bare POST {"response": "..."} from tests / form
            if rsvp_form.is_valid() or request.POST.get("response"):
                response = (
                    rsvp_form.cleaned_data["response"]
                    if rsvp_form.is_valid()
                    else request.POST.get("response")
                )
                try:
                    set_participant_response(
                        participant, response, user=request.user
                    )
                    messages.success(request, _("Response recorded."))
                    return redirect("my-meeting-detail", pk=pk)
                except ValueError as exc:
                    messages.error(request, str(exc))
                    return redirect("my-meeting-detail", pk=pk)

    show_online = participant.status in {
        "INVITED",
        "ACCEPTED",
        "ATTENDED",
    }
    return render(
        request,
        "dashboard/governance/my_meeting_detail.html",
        {
            "meeting": meeting,
            "participant": participant,
            "rsvp_form": rsvp_form if participant.status == "INVITED" else None,
            "show_online": show_online,
            "agenda_items": meeting.agenda_items.all(),
        },
    )


@login_required
@require_http_methods(["GET"])
def my_resolutions(request):
    member = _member_profile(request.user)
    if member is None:
        return _deny()
    pending = (
        ResolutionSigner.objects.filter(member=member, signed_at__isnull=True)
        .exclude(resolution__status=ResolutionStatus.WITHDRAWN)
        .select_related("resolution", "resolution__meeting", "version")
        .order_by("-selected_at")
    )
    signed = (
        ResolutionSigner.objects.filter(member=member, signed_at__isnull=False)
        .select_related("resolution", "resolution__meeting")
        .order_by("-signed_at")
    )
    return render(
        request,
        "dashboard/governance/my_resolutions.html",
        {"pending": pending, "signed": signed},
    )


def _member_can_view_resolution(member, resolution: Resolution) -> ResolutionSigner | None:
    return (
        ResolutionSigner.objects.filter(
            resolution=resolution,
            member=member,
            version=resolution.current_version,
        )
        .select_related("version")
        .first()
    )


@login_required
@require_http_methods(["GET"])
def my_resolution_detail(request, pk):
    member = _member_profile(request.user)
    if member is None:
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related("current_version", "meeting"),
        pk=pk,
    )
    signer = _member_can_view_resolution(member, resolution)
    if signer is None:
        messages.error(request, _("You are not authorized to view this resolution."))
        return redirect("my-resolutions")
    can_sign = (
        signer.signed_at is None
        and resolution.status
        in {
            ResolutionStatus.READY_FOR_SIGNING,
            ResolutionStatus.PARTIALLY_SIGNED,
        }
        and bool(member.signature_image)
    )
    return render(
        request,
        "dashboard/governance/my_resolution_detail.html",
        {
            "resolution": resolution,
            "version": resolution.current_version,
            "signer": signer,
            "can_sign": can_sign,
            "has_signature": bool(member.signature_image),
            "can_download": True,
        },
    )


@login_required
@require_http_methods(["GET"])
def my_resolution_document_pdf(request, pk):
    member = _member_profile(request.user)
    if member is None:
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related("current_version", "meeting"),
        pk=pk,
    )
    if _member_can_view_resolution(member, resolution) is None:
        messages.error(request, _("You are not authorized to download this document."))
        return redirect("my-resolutions")
    return resolution_file_response(resolution, fmt="pdf", actor=request.user)


@login_required
@require_http_methods(["GET"])
def my_resolution_document_docx(request, pk):
    member = _member_profile(request.user)
    if member is None:
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related("current_version", "meeting"),
        pk=pk,
    )
    if _member_can_view_resolution(member, resolution) is None:
        messages.error(request, _("You are not authorized to download this document."))
        return redirect("my-resolutions")
    return resolution_file_response(resolution, fmt="docx", actor=request.user)


@login_required
@require_http_methods(["GET", "POST"])
def my_resolution_sign(request, pk):
    member = _member_profile(request.user)
    if member is None:
        return _deny()
    resolution = get_object_or_404(
        Resolution.objects.select_related("current_version", "meeting"),
        pk=pk,
    )
    signer = _member_can_view_resolution(member, resolution)
    if signer is None or signer.signed_at is not None:
        messages.error(request, _("You cannot sign this resolution."))
        return redirect("my-resolutions")

    form = ResolutionSignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            sign_resolution(
                resolution,
                member,
                user=request.user,
                request=request,
                confirmation=True,
            )
            messages.success(request, _("Resolution approved and signed."))
            return redirect("my-resolution-detail", pk=pk)
        except ValueError as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "dashboard/governance/my_resolution_sign.html",
        {
            "resolution": resolution,
            "version": resolution.current_version,
            "form": form,
            "member": member,
            "has_signature": bool(member.signature_image),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def my_signature(request):
    """Member digital signature upload / replace / remove (profile only)."""
    member = _member_profile(request.user)
    if member is None:
        messages.info(request, _("No member profile is linked to this account."))
        return _deny()

    form = MemberSignatureForm()
    if request.method == "POST":
        action = (request.POST.get("action") or "upload").strip()
        if action == "remove":
            if member.signature_image:
                member.signature_image.delete(save=False)
                member.signature_image = None
                member.signature_uploaded_at = None
                member.save(
                    update_fields=["signature_image", "signature_uploaded_at", "updated_at"]
                )
                messages.success(request, _("Digital signature removed from your profile."))
            else:
                messages.info(request, _("No signature is configured."))
            return redirect("my-signature")

        form = MemberSignatureForm(request.POST, request.FILES)
        if form.is_valid():
            if member.signature_image:
                member.signature_image.delete(save=False)
            member.signature_image = form.cleaned_data["signature_image"]
            member.signature_uploaded_at = timezone.now()
            member.save(
                update_fields=["signature_image", "signature_uploaded_at", "updated_at"]
            )
            messages.success(
                request,
                _("Digital signature saved. Historical signed resolutions are unchanged."),
            )
            return redirect("my-signature")
        messages.error(request, _("Could not save signature. Check the file and try again."))

    return render(
        request,
        "dashboard/governance/my_signature.html",
        {
            "member": member,
            "form": form,
            "has_signature": bool(member.signature_image),
            "signature_uploaded_at": member.signature_uploaded_at,
        },
    )
