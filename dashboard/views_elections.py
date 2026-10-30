"""Admin dashboard views for the production election engine + member entrypoints."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from rbac.permissions import has_action
from voting import views as member_views
from voting.forms import ElectionCandidateFormSet, ElectionForm, ElectionQuestionFormSet
from voting.models import Election, ElectionStatus, ElectionType
from voting.services import (
    ElectionError,
    cancel_election,
    close_election,
    compute_results,
    ensure_closed_if_expired,
    extend_election,
    finalize_election,
    frozen_electorate_count,
    open_election,
    preview_stats,
    publish_results,
    restart_election,
    schedule_election,
    turnout_met,
)


def _deny(request, action="view"):
    return not has_action(request.user, "elections", action)


# Member entrypoints under /dashboard/my-elections/
my_elections_entry = member_views.my_elections
my_election_cast_entry = member_views.my_election_cast
my_election_results_entry = member_views.my_election_results


@login_required
def elections_list(request):
    if _deny(request, "view"):
        return redirect("dashboard")
    from django.core.paginator import Paginator

    elections = list(Election.objects.all().order_by("-created_at"))
    for e in elections:
        if e.status == ElectionStatus.OPEN:
            ensure_closed_if_expired(e)
    page_obj = Paginator(elections, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/elections/list.html",
        {
            "elections": page_obj,
            "page_obj": page_obj,
            "can_create": has_action(request.user, "elections", "create"),
            "can_edit": has_action(request.user, "elections", "edit"),
            "can_manage": has_action(request.user, "elections", "manage"),
        },
    )


@login_required
def election_create(request):
    if _deny(request, "create"):
        return redirect("dashboard-elections")
    if request.method == "POST":
        form = ElectionForm(request.POST)
        formset = ElectionCandidateFormSet(request.POST)
        qformset = ElectionQuestionFormSet(request.POST)
        if form.is_valid() and formset.is_valid() and qformset.is_valid():
            election = form.save(commit=False)
            election.created_by = request.user
            election.status = ElectionStatus.DRAFT
            if election.election_type == ElectionType.ADVISORY_COUNCIL:
                election.auto_candidates = True
                election.allow_self_vote = False
            election.save()
            form.save_m2m()
            if not election.auto_candidates:
                formset.instance = election
                formset.save()
            qformset.instance = election
            qformset.save()
            messages.success(request, _("Election created."))
            return redirect("dashboard-election-detail", pk=election.pk)
    else:
        form = ElectionForm(
            initial={
                "election_type": ElectionType.ADVISORY_COUNCIL,
                "window_hours": 48,
                "auto_candidates": True,
                "allow_self_vote": False,
                "quorum_numerator": 2,
                "quorum_denominator": 3,
                "total_seats": 5,
            }
        )
        formset = ElectionCandidateFormSet()
        qformset = ElectionQuestionFormSet()
    return render(
        request,
        "dashboard/elections/form.html",
        {
            "form": form,
            "formset": formset,
            "qformset": qformset,
            "is_create": True,
            "preview": None,
        },
    )


@login_required
def election_edit(request, pk):
    if _deny(request, "edit"):
        return redirect("dashboard-elections")
    election = get_object_or_404(Election, pk=pk)
    if election.configuration_locked() and request.method == "POST":
        # Allow only description/title edits when locked
        pass
    if request.method == "POST":
        form = ElectionForm(request.POST, instance=election)
        formset = ElectionCandidateFormSet(request.POST, instance=election)
        qformset = ElectionQuestionFormSet(request.POST, instance=election)
        if form.is_valid() and (
            election.auto_candidates or formset.is_valid()
        ) and qformset.is_valid():
            form.save()
            if not election.auto_candidates and not election.configuration_locked():
                formset.save()
            if not election.configuration_locked():
                qformset.save()
            messages.success(request, _("Election saved."))
            return redirect("dashboard-election-detail", pk=election.pk)
    else:
        form = ElectionForm(instance=election)
        formset = ElectionCandidateFormSet(instance=election)
        qformset = ElectionQuestionFormSet(instance=election)
    return render(
        request,
        "dashboard/elections/form.html",
        {
            "form": form,
            "formset": formset,
            "qformset": qformset,
            "election": election,
            "is_create": False,
            "preview": preview_stats(election),
            "locked": election.configuration_locked(),
        },
    )


@login_required
def election_detail(request, pk):
    if _deny(request, "view"):
        return redirect("dashboard")
    election = get_object_or_404(Election, pk=pk)
    ensure_closed_if_expired(election)
    election.refresh_from_db()
    results = compute_results(election)
    preview = preview_stats(election)
    return render(
        request,
        "dashboard/elections/detail.html",
        {
            "election": election,
            "results": results,
            "eligible_count": frozen_electorate_count(election)
            if election.electorate_frozen_at
            else preview["eligible_count"],
            "candidate_count": election.candidates.filter(is_active=True).count(),
            "preview": preview,
            "turnout_ok": turnout_met(election),
            "can_edit": has_action(request.user, "elections", "edit"),
            "can_manage": has_action(request.user, "elections", "manage"),
            "can_delete": has_action(request.user, "elections", "delete"),
            "now": timezone.now(),
        },
    )


@login_required
@require_POST
def election_action(request, pk):
    if _deny(request, "manage"):
        messages.error(request, _("You don't have permission to manage elections."))
        return redirect("dashboard-election-detail", pk=pk)

    election = get_object_or_404(Election, pk=pk)
    action = (request.POST.get("action") or "").strip().lower()
    try:
        if action == "schedule":
            schedule_election(election, actor=request.user)
            messages.success(request, _("Election scheduled."))
        elif action == "open":
            open_election(election, actor=request.user)
            messages.success(request, _("Election opened. Electorate frozen."))
        elif action == "close":
            close_election(election, actor=request.user)
            messages.success(request, _("Election closed."))
        elif action == "extend":
            raw = (request.POST.get("new_end_at") or "").strip()
            new_end = parse_datetime(raw)
            if new_end is None:
                raise ElectionError(_("Invalid end time."))
            if timezone.is_naive(new_end):
                new_end = timezone.make_aware(new_end, timezone.get_current_timezone())
            extend_election(election, new_end, actor=request.user)
            messages.success(request, _("Election extended."))
        elif action == "restart":
            confirm = request.POST.get("confirm_restart") == "1"
            restart_election(election, actor=request.user, confirm=confirm)
            messages.success(request, _("Election restarted. Ballots cleared."))
        elif action == "finalize":
            override = request.POST.get("admin_override") == "1"
            finalize_election(
                election,
                actor=request.user,
                admin_override=override,
                notes=request.POST.get("notes") or "",
            )
            messages.success(request, _("Election finalized."))
        elif action == "publish":
            publish_results(election, actor=request.user)
            messages.success(request, _("Results published."))
        elif action == "cancel":
            cancel_election(
                election, actor=request.user, notes=request.POST.get("notes") or ""
            )
            messages.success(request, _("Election cancelled."))
        else:
            messages.error(request, _("Unknown action."))
    except ElectionError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard-election-detail", pk=pk)


@login_required
@require_POST
def election_delete(request, pk):
    if _deny(request, "delete"):
        messages.error(request, _("You don't have permission to delete elections."))
        return redirect("dashboard-elections")
    election = get_object_or_404(Election, pk=pk)
    if election.status == ElectionStatus.OPEN:
        messages.error(request, _("Close the election before deleting."))
        return redirect("dashboard-election-detail", pk=pk)
    election.delete()
    messages.success(request, _("Election deleted."))
    return redirect("dashboard-elections")
