"""Member-facing election views. Legacy Vote product path is disabled."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from accounts.models import Role
from voting.forms import ChoiceBallotForm, RankedBallotForm
from voting.models import (
    Election,
    ElectionOption,
    ElectionParticipation,
    ElectionStatus,
    ElectionType,
)
from voting.services import (
    ElectionError,
    candidates_for_voter,
    cast_choice_ballot,
    cast_ranked_ballot,
    compute_results,
    ensure_closed_if_expired,
    preview_stats,
    required_ranks_for_voter,
    user_is_eligible,
)


def member_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.role not in (Role.MEMBER, Role.SUPER_ADMIN, Role.EXECUTIVE_ADMIN):
            messages.error(request, _("Access denied."))
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
def legacy_voting_redirect(request, pk=None):
    """Legacy Vote/VoteRecord product path — redirect to My Elections."""
    messages.info(request, _("Voting has moved to My Elections."))
    return redirect("my-elections")


@login_required
@member_required
def my_elections(request):
    now = timezone.now()
    open_qs = Election.objects.filter(status=ElectionStatus.OPEN)
    for e in open_qs:
        ensure_closed_if_expired(e)

    open_qs = Election.objects.filter(status=ElectionStatus.OPEN).filter(
        Q(start_at__isnull=True) | Q(start_at__lte=now),
        Q(end_at__isnull=True) | Q(end_at__gt=now),
    )
    open_elections = [e for e in open_qs if user_is_eligible(e, request.user)]

    voted_ids = set(
        ElectionParticipation.objects.filter(user=request.user).values_list(
            "election_id", flat=True
        )
    )

    # Closed / finalized where user was in electorate
    history = (
        Election.objects.filter(
            electorate__user=request.user,
            status__in=(
                ElectionStatus.CLOSED,
                ElectionStatus.FINALIZED,
                ElectionStatus.OPEN,
            ),
        )
        .distinct()
        .order_by("-end_at", "-created_at")[:40]
    )

    published = Election.objects.filter(
        results_published=True, electorate__user=request.user
    ).distinct().order_by("-end_at")[:20]

    return render(
        request,
        "voting/my_elections.html",
        {
            "open_elections": open_elections,
            "voted_ids": voted_ids,
            "history": history,
            "published": published,
            "now": now,
        },
    )


@login_required
@member_required
@require_http_methods(["GET", "POST"])
def my_election_cast(request, pk):
    election = get_object_or_404(Election, pk=pk)
    ensure_closed_if_expired(election)
    election.refresh_from_db()

    if not user_is_eligible(election, request.user):
        messages.error(request, _("You are not eligible to vote in this election."))
        return redirect("my-elections")
    if ElectionParticipation.objects.filter(election=election, user=request.user).exists():
        messages.warning(request, _("You have already voted."))
        return redirect("my-elections")
    if election.status != ElectionStatus.OPEN:
        messages.error(request, _("This election is not open for voting."))
        return redirect("my-elections")

    if election.is_ranked:
        return _cast_ranked(request, election)
    return _cast_choice(request, election)


def _cast_ranked(request, election):
    candidates = candidates_for_voter(election, request.user)
    required = required_ranks_for_voter(election, request.user)
    if required < 1:
        messages.error(request, _("No candidates available for you to rank."))
        return redirect("my-elections")

    if request.method == "POST":
        form = RankedBallotForm(
            request.POST, candidates=candidates, required_count=required
        )
        if form.is_valid():
            try:
                cast_ranked_ballot(
                    election,
                    request.user,
                    form.cleaned_data["ordered_candidate_ids"],
                )
                messages.success(request, _("Your vote has been recorded."))
                return redirect("my-elections")
            except ElectionError as exc:
                messages.error(request, str(exc))
    else:
        form = RankedBallotForm(candidates=candidates, required_count=required)

    stats = preview_stats(election)
    return render(
        request,
        "voting/election_cast.html",
        {
            "election": election,
            "form": form,
            "candidates": candidates,
            "required_count": required,
            "stats": stats,
            "is_advisory": election.election_type == ElectionType.ADVISORY_COUNCIL,
        },
    )


def _cast_choice(request, election):
    options = list(
        ElectionOption.objects.filter(
            question__election=election,
            question__is_active=True,
            is_active=True,
        ).select_related("question").order_by(
            "question__display_order", "display_order"
        )
    )
    if not options:
        messages.error(request, _("No options available."))
        return redirect("my-elections")

    multiple = bool(
        election.election_type == ElectionType.MULTI_CHOICE
        and election.allow_multiple_selections
    )
    max_sel = election.max_selections if multiple else 1

    if request.method == "POST":
        form = ChoiceBallotForm(
            request.POST, options=options, multiple=multiple, max_selections=max_sel
        )
        if form.is_valid():
            try:
                cast_choice_ballot(
                    election, request.user, form.cleaned_data["option_ids"]
                )
                messages.success(request, _("Your vote has been recorded."))
                return redirect("my-elections")
            except ElectionError as exc:
                messages.error(request, str(exc))
    else:
        form = ChoiceBallotForm(
            options=options, multiple=multiple, max_selections=max_sel
        )

    return render(
        request,
        "voting/election_choice_cast.html",
        {
            "election": election,
            "form": form,
            "options": options,
        },
    )


@login_required
@member_required
def my_election_results(request, pk):
    election = get_object_or_404(Election, pk=pk)
    if not election.results_published:
        messages.error(request, _("Results are not published yet."))
        return redirect("my-elections")
    if not election.electorate.filter(user=request.user).exists() and not user_is_eligible(
        election, request.user
    ):
        # Allow published results for electorate members; others denied
        messages.error(request, _("Results are not available for your account."))
        return redirect("my-elections")
    results = compute_results(election)
    return render(
        request,
        "voting/election_results.html",
        {"election": election, "results": results},
    )


# Backward-compatible aliases used by older URL names
election_member_list = my_elections
election_member_cast = my_election_cast
election_member_results = my_election_results
voting_list = legacy_voting_redirect
voting_cast = legacy_voting_redirect
voting_results = legacy_voting_redirect
