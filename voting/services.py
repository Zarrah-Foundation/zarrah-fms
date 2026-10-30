"""Election lifecycle, eligibility freeze, ranked/choice ballots, and results."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Iterable, Optional

from django.db import IntegrityError, transaction
from django.db.models import Count, QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _

from members.models import Member, MemberStatus
from voting.models import (
    Election,
    ElectionAdminAction,
    ElectionBallot,
    ElectionBallotChoice,
    ElectionBallotPreference,
    ElectionCandidate,
    ElectionElectorate,
    ElectionOption,
    ElectionParticipation,
    ElectionQuestion,
    ElectionStatus,
    ElectionType,
    EligibilityMode,
)


class ElectionError(Exception):
    """Domain error for election operations."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def founder_reserved_seats(total_seats: int) -> int:
    return math.ceil(total_seats / 2) if total_seats else 0


def elected_seats(total_seats: int) -> int:
    return max(0, total_seats - founder_reserved_seats(total_seats))


# Advisory Council constitutional constants (not admin-configurable).
AC_QUORUM_NUMERATOR = 2
AC_QUORUM_DENOMINATOR = 3
AC_WINDOW_HOURS = 48


def apply_advisory_council_constitution(election: Election) -> Election:
    """Force Advisory Council hard rules onto an election instance (in memory)."""
    if election.election_type != ElectionType.ADVISORY_COUNCIL:
        return election
    election.quorum_numerator = AC_QUORUM_NUMERATOR
    election.quorum_denominator = AC_QUORUM_DENOMINATOR
    election.window_hours = AC_WINDOW_HOURS
    election.auto_candidates = True
    election.allow_self_vote = False
    election.eligibility_mode = EligibilityMode.ALL_APPROVED
    return election


def effective_quorum_ratio(election: Election) -> float:
    """Runtime quorum ratio — AC is always exactly 2/3 regardless of stored fields."""
    if election.election_type == ElectionType.ADVISORY_COUNCIL:
        return AC_QUORUM_NUMERATOR / AC_QUORUM_DENOMINATOR
    return election.quorum_ratio


def is_founder_member(member: Optional[Member]) -> bool:
    if member is None:
        return False
    if getattr(member, "is_founder", False):
        return True
    mtype = getattr(member, "membership_type", None)
    if mtype is not None and (getattr(mtype, "slug", "") or "").lower() == "founder":
        return True
    return False


def _audit(election: Election, actor, action: str, notes: str = "") -> None:
    ElectionAdminAction.objects.create(
        election=election,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        notes=notes or "",
    )


def ensure_closed_if_expired(election: Election, actor=None) -> Election:
    """Soft-close when end_at has passed. Safe to call on every cast/list."""
    if election.status != ElectionStatus.OPEN:
        return election
    now = timezone.now()
    if election.end_at and now >= election.end_at:
        election.status = ElectionStatus.CLOSED
        election.save(update_fields=["status", "updated_at"])
        _audit(election, actor, "AUTO_CLOSE", notes="end_at reached")
        return election
    try:
        from voting.notifications import maybe_notify_election_closing_soon

        maybe_notify_election_closing_soon(election)
    except Exception:
        pass
    return election


# ---------------------------------------------------------------------------
# Eligibility (pre-freeze) + freeze
# ---------------------------------------------------------------------------


def eligible_members_qs(election: Election) -> QuerySet:
    """Live eligibility BEFORE freeze. After freeze, prefer frozen_electorate_qs."""
    if election.electorate_frozen_at:
        member_ids = election.electorate.values_list("member_id", flat=True)
        return Member.objects.filter(pk__in=member_ids).select_related(
            "user", "membership_type"
        )

    qs = Member.objects.filter(status=MemberStatus.APPROVED).exclude(user__isnull=True)
    qs = qs.select_related("user", "membership_type")

    mode = election.eligibility_mode or EligibilityMode.ALL_APPROVED
    # Legacy bridge
    if (
        mode == EligibilityMode.ALL_APPROVED
        and not election.eligible_approved_members_only
        and election.pk
        and not election.membership_types.exists()
        and not election.member_groups.exists()
    ):
        # Historical broad eligibility: still APPROVED-only per Phase 5 lock.
        pass

    if mode == EligibilityMode.BY_MEMBERSHIP_TYPES:
        type_ids = list(election.membership_types.values_list("pk", flat=True))
        if not type_ids:
            return qs.none()
        qs = qs.filter(membership_type_id__in=type_ids)
    elif mode == EligibilityMode.BY_GROUPS:
        group_ids = list(election.member_groups.values_list("pk", flat=True))
        if not group_ids:
            return qs.none()
        qs = qs.filter(group_memberships__group_id__in=group_ids).distinct()
    return qs


def frozen_electorate_qs(election: Election) -> QuerySet:
    return election.electorate.select_related("member", "user")


def frozen_electorate_count(election: Election) -> int:
    if election.electorate_frozen_at:
        return election.electorate.count()
    return eligible_members_qs(election).count()


def eligible_user_ids(election: Election) -> set:
    if election.electorate_frozen_at:
        return set(election.electorate.values_list("user_id", flat=True))
    return set(eligible_members_qs(election).values_list("user_id", flat=True))


def user_is_eligible(election: Election, user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if election.electorate_frozen_at:
        return election.electorate.filter(user=user).exists()
    return eligible_members_qs(election).filter(user=user).exists()


@transaction.atomic
def freeze_electorate(election: Election) -> int:
    """Create immutable ElectionElectorate rows. Idempotent if already frozen."""
    if election.electorate_frozen_at:
        return election.electorate.count()
    now = timezone.now()
    members = list(eligible_members_qs(election).filter(user__isnull=False))
    ElectionElectorate.objects.bulk_create(
        [
            ElectionElectorate(
                election=election,
                member=m,
                user=m.user,
                frozen_at=now,
            )
            for m in members
            if m.user_id
        ],
        ignore_conflicts=True,
    )
    election.electorate_frozen_at = now
    election.save(update_fields=["electorate_frozen_at", "updated_at"])
    return election.electorate.count()


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


def _member_display_name(member: Member) -> str:
    return f"{member.first_name} {member.last_name}".strip() or member.member_id


@transaction.atomic
def sync_auto_candidates(election: Election) -> int:
    """Create/activate candidates from frozen (or live) eligible members."""
    if election.candidates_locked:
        return election.candidates.filter(is_active=True).count()

    members = list(eligible_members_qs(election))
    existing = {
        str(c.member_id): c
        for c in election.candidates.filter(member__isnull=False).select_related("member")
    }
    keep_member_ids = set()
    order = 0
    for member in members:
        keep_member_ids.add(str(member.pk))
        cand = existing.get(str(member.pk))
        if cand is None:
            ElectionCandidate.objects.create(
                election=election,
                member=member,
                name=_member_display_name(member),
                is_founder_candidate=is_founder_member(member),
                display_order=order,
                is_active=True,
            )
        else:
            cand.name = _member_display_name(member)
            cand.is_founder_candidate = is_founder_member(member)
            cand.display_order = order
            cand.is_active = True
            cand.save()
        order += 1

    # Deactivate candidates no longer eligible (pre-lock only)
    for mid, cand in existing.items():
        if mid not in keep_member_ids:
            cand.is_active = False
            cand.save(update_fields=["is_active"])
    return election.candidates.filter(is_active=True).count()


def candidates_for_voter(election: Election, user) -> list:
    """Active candidates excluding the voter's own candidate when self-vote banned."""
    qs = election.candidates.filter(is_active=True).select_related("member").order_by(
        "display_order", "name"
    )
    candidates = list(qs)
    if election.allow_self_vote:
        return candidates
    try:
        member = user.member_profile
    except Member.DoesNotExist:
        return candidates
    return [c for c in candidates if c.member_id != member.pk]


def required_ranks_for_voter(election: Election, user) -> int:
    available = candidates_for_voter(election, user)
    return min(election.total_seats or 1, len(available))


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def schedule_election(election: Election, actor=None) -> Election:
    if election.status != ElectionStatus.DRAFT:
        raise ElectionError(_("Only draft elections can be scheduled."))
    election.status = ElectionStatus.SCHEDULED
    election.save(update_fields=["status", "updated_at"])
    _audit(election, actor, "SCHEDULE")
    return election


@transaction.atomic
def open_election(election: Election, actor=None) -> Election:
    if election.status not in (
        ElectionStatus.DRAFT,
        ElectionStatus.SCHEDULED,
    ):
        raise ElectionError(
            _("Election cannot be opened from status %(status)s.")
            % {"status": election.status}
        )
    if election.is_choice and not election.questions.filter(is_active=True).exists():
        raise ElectionError(_("Add at least one active question before opening."))

    now = timezone.now()
    election.status = ElectionStatus.OPEN
    if not election.start_at:
        election.start_at = now

    # Advisory Council: constitutional 48h window + 2/3 quorum (not admin-weakened).
    if election.election_type == ElectionType.ADVISORY_COUNCIL:
        apply_advisory_council_constitution(election)
        election.end_at = election.start_at + timedelta(hours=AC_WINDOW_HOURS)
    elif not election.end_at:
        hours = election.window_hours or 48
        election.end_at = election.start_at + timedelta(hours=hours)

    election.save()

    freeze_electorate(election)
    if election.auto_candidates or election.election_type == ElectionType.ADVISORY_COUNCIL:
        sync_auto_candidates(election)

    if election.is_choice and election.election_type == ElectionType.YES_NO:
        _ensure_yes_no_options(election)

    _audit(election, actor, "OPEN")
    try:
        from voting.notifications import notify_election_opened

        notify_election_opened(election)
    except Exception:
        pass
    return election


def _ensure_yes_no_options(election: Election) -> None:
    q = election.questions.filter(is_active=True).order_by("display_order").first()
    if q is None:
        q = ElectionQuestion.objects.create(
            election=election,
            question_en=election.title_en,
            question_bn=election.title_bn or "",
        )
    if not q.options.exists():
        ElectionOption.objects.bulk_create(
            [
                ElectionOption(
                    question=q, label_en="Yes", label_bn="হ্যাঁ", display_order=0
                ),
                ElectionOption(
                    question=q, label_en="No", label_bn="না", display_order=1
                ),
            ]
        )


def close_election(election: Election, actor=None) -> Election:
    if election.status != ElectionStatus.OPEN:
        raise ElectionError(_("Only open elections can be closed."))
    election.status = ElectionStatus.CLOSED
    election.save(update_fields=["status", "updated_at"])
    _audit(election, actor, "CLOSE")
    return election


def extend_election(election: Election, new_end_at, actor=None) -> Election:
    if new_end_at is None:
        raise ElectionError(_("New end time is required."))
    if election.status not in (ElectionStatus.OPEN, ElectionStatus.CLOSED):
        raise ElectionError(_("Election cannot be extended in this status."))
    if election.status == ElectionStatus.FINALIZED:
        raise ElectionError(_("Finalized elections cannot be extended."))
    if election.start_at and new_end_at <= election.start_at:
        raise ElectionError(_("End time must be after start time."))
    now = timezone.now()
    if new_end_at <= now:
        raise ElectionError(_("End time must be in the future."))
    election.end_at = new_end_at
    if election.status == ElectionStatus.CLOSED:
        election.status = ElectionStatus.OPEN
    election.save()
    _audit(
        election,
        actor,
        "EXTEND",
        notes=f"new_end_at={new_end_at.isoformat()}",
    )
    return election


@transaction.atomic
def restart_election(election: Election, actor=None, *, confirm: bool = False) -> Election:
    if not confirm:
        raise ElectionError(_("Restart requires explicit confirmation."))
    if election.status == ElectionStatus.OPEN and election.participations.exists():
        raise ElectionError(_("Close the election before restarting while ballots exist."))
    ElectionBallotPreference.objects.filter(ballot__election=election).delete()
    ElectionBallotChoice.objects.filter(ballot__election=election).delete()
    ElectionBallot.objects.filter(election=election).delete()
    ElectionParticipation.objects.filter(election=election).delete()
    ElectionElectorate.objects.filter(election=election).delete()
    election.status = ElectionStatus.DRAFT
    election.results_published = False
    election.start_at = None
    election.end_at = None
    election.electorate_frozen_at = None
    election.candidates_locked = False
    election.save()
    _audit(election, actor, "RESTART", notes="ballots and freeze cleared")
    return election


def cancel_election(election: Election, actor=None, notes: str = "") -> Election:
    if election.status == ElectionStatus.FINALIZED:
        raise ElectionError(_("Finalized elections cannot be cancelled."))
    election.status = ElectionStatus.CANCELLED
    election.save(update_fields=["status", "updated_at"])
    _audit(election, actor, "CANCEL", notes=notes)
    return election


def turnout_met(election: Election) -> bool:
    eligible = frozen_electorate_count(election)
    if eligible <= 0:
        return False
    votes = election.participations.count()
    required = math.ceil(eligible * effective_quorum_ratio(election))
    return votes >= required


def quorum_required(election: Election) -> int:
    eligible = frozen_electorate_count(election)
    if eligible <= 0:
        return 0
    return math.ceil(eligible * effective_quorum_ratio(election))


def finalize_election(
    election: Election,
    actor=None,
    *,
    admin_override: bool = False,
    notes: str = "",
) -> Election:
    election = ensure_closed_if_expired(election, actor=actor)
    if election.status != ElectionStatus.CLOSED:
        raise ElectionError(_("Election must be closed before finalization."))
    met = turnout_met(election)
    if not met and not admin_override:
        raise ElectionError(_("Turnout quorum not met."))
    if not met and admin_override and not (notes or "").strip():
        raise ElectionError(_("Override requires an audit reason."))
    election.status = ElectionStatus.FINALIZED
    election.save(update_fields=["status", "updated_at"])
    action_notes = notes or ""
    if admin_override and not met:
        action_notes = (action_notes + " | override=turnout").strip(" |")
    _audit(election, actor, "FINALIZE", notes=action_notes)
    return election


def publish_results(election: Election, actor=None) -> Election:
    if election.status not in (ElectionStatus.FINALIZED, ElectionStatus.CLOSED):
        raise ElectionError(_("Publish after close/finalize."))
    if election.status == ElectionStatus.CLOSED and not election.results_published:
        # Prefer finalized first, but allow publish after finalize only ideally.
        # Spec: FINALIZED → PUBLISHED (flag). Require FINALIZED.
        raise ElectionError(_("Finalize the election before publishing results."))
    election.results_published = True
    election.save(update_fields=["results_published", "updated_at"])
    _audit(election, actor, "PUBLISH_RESULTS")
    try:
        from voting.notifications import notify_election_results_available

        notify_election_results_available(election)
    except Exception:
        pass
    return election


def _assert_open_window(election: Election) -> Election:
    election = ensure_closed_if_expired(election)
    if election.status != ElectionStatus.OPEN:
        raise ElectionError(_("Election is not open."))
    now = timezone.now()
    if election.start_at and now < election.start_at:
        raise ElectionError(_("Election has not started yet."))
    if election.end_at and now >= election.end_at:
        ensure_closed_if_expired(election)
        raise ElectionError(_("Election voting window has ended."))
    return election


# ---------------------------------------------------------------------------
# Cast ballots
# ---------------------------------------------------------------------------


def cast_ranked_ballot(
    election: Election,
    user,
    ordered_candidate_ids: Iterable,
) -> ElectionBallot:
    # Soft-close must commit even if the cast is rejected (separate from ballot txn).
    election = _assert_open_window(election)
    return _cast_ranked_ballot_atomic(election, user, ordered_candidate_ids)


@transaction.atomic
def _cast_ranked_ballot_atomic(
    election: Election,
    user,
    ordered_candidate_ids: Iterable,
) -> ElectionBallot:
    if election.status != ElectionStatus.OPEN:
        raise ElectionError(_("Election is not open."))
    if not election.is_ranked:
        raise ElectionError(_("This election does not accept ranked ballots."))

    if not user_is_eligible(election, user):
        raise ElectionError(_("You are not eligible to vote in this election."))

    if ElectionParticipation.objects.filter(election=election, user=user).exists():
        raise ElectionError(_("You have already voted."))

    ordered = [cid for cid in ordered_candidate_ids if cid]
    seen = set()
    unique_ordered = []
    for cid in ordered:
        key = str(cid)
        if key in seen:
            continue
        seen.add(key)
        unique_ordered.append(cid)

    available = candidates_for_voter(election, user)
    active_ids = {str(c.pk) for c in available}
    if not unique_ordered:
        raise ElectionError(_("Please rank at least one candidate."))

    for cid in unique_ordered:
        if str(cid) not in active_ids:
            raise ElectionError(_("Invalid candidate selection."))

    # Explicit self-vote rejection (also covers crafted requests)
    if not election.allow_self_vote:
        try:
            member = user.member_profile
        except Member.DoesNotExist:
            member = None
        if member is not None:
            own = election.candidates.filter(member=member, is_active=True).first()
            if own and str(own.pk) in {str(x) for x in unique_ordered}:
                raise ElectionError(_("Self-voting is not allowed."))

    required = required_ranks_for_voter(election, user)
    if required < 1:
        raise ElectionError(_("No candidates available for you to rank."))
    if len(unique_ordered) != required:
        raise ElectionError(
            _("You must rank exactly %(count)s candidates.") % {"count": required}
        )

    try:
        ElectionParticipation.objects.create(election=election, user=user)
    except IntegrityError as exc:
        raise ElectionError(_("You have already voted.")) from exc
    ballot = ElectionBallot.objects.create(election=election)
    prefs = [
        ElectionBallotPreference(ballot=ballot, candidate_id=cid, rank=rank)
        for rank, cid in enumerate(unique_ordered, start=1)
    ]
    ElectionBallotPreference.objects.bulk_create(prefs)
    if not election.candidates_locked:
        election.candidates_locked = True
        election.save(update_fields=["candidates_locked", "updated_at"])
    return ballot


def cast_choice_ballot(
    election: Election,
    user,
    option_ids: Iterable,
) -> ElectionBallot:
    election = _assert_open_window(election)
    return _cast_choice_ballot_atomic(election, user, option_ids)


@transaction.atomic
def _cast_choice_ballot_atomic(
    election: Election,
    user,
    option_ids: Iterable,
) -> ElectionBallot:
    if election.status != ElectionStatus.OPEN:
        raise ElectionError(_("Election is not open."))
    if not election.is_choice:
        raise ElectionError(_("This election does not accept choice ballots."))

    if not user_is_eligible(election, user):
        raise ElectionError(_("You are not eligible to vote in this election."))

    if ElectionParticipation.objects.filter(election=election, user=user).exists():
        raise ElectionError(_("You have already voted."))

    selected = []
    seen = set()
    for oid in option_ids:
        if not oid:
            continue
        key = str(oid)
        if key in seen:
            continue
        seen.add(key)
        selected.append(oid)

    if not selected:
        raise ElectionError(_("Please select an option."))

    valid = set(
        ElectionOption.objects.filter(
            question__election=election,
            question__is_active=True,
            is_active=True,
        ).values_list("pk", flat=True)
    )
    valid_str = {str(v) for v in valid}
    for oid in selected:
        if str(oid) not in valid_str:
            raise ElectionError(_("Invalid option selection."))

    if election.election_type == ElectionType.YES_NO:
        if len(selected) != 1:
            raise ElectionError(_("Select exactly one option (Yes or No)."))
    else:
        max_sel = election.max_selections or 1
        if not election.allow_multiple_selections:
            max_sel = 1
        if len(selected) > max_sel:
            raise ElectionError(
                _("You may select at most %(n)s option(s).") % {"n": max_sel}
            )

    try:
        ElectionParticipation.objects.create(election=election, user=user)
    except IntegrityError as exc:
        raise ElectionError(_("You have already voted.")) from exc
    ballot = ElectionBallot.objects.create(election=election)
    ElectionBallotChoice.objects.bulk_create(
        [ElectionBallotChoice(ballot=ballot, option_id=oid) for oid in selected]
    )
    return ballot


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


def compute_results(election: Election) -> dict:
    """
    Aggregate results.

    Ranked: Borda points ``N - rank + 1`` where ``N = total_seats``.
    Advisory Council: fill ceil(N/2) founder-reserved seats first, then elected seats.
    Ties broken by candidate name (ascending) for determinism.
    Choice elections: option counts.
    """
    turnout = {
        "votes": election.participations.count(),
        "eligible": frozen_electorate_count(election),
        "quorum_met": turnout_met(election),
        "required": quorum_required(election),
    }

    if election.is_choice:
        options = ElectionOption.objects.filter(
            question__election=election, is_active=True
        ).annotate(votes=Count("ballot_choices"))
        scores = [
            {
                "option_id": str(o.pk),
                "label": o.label_en,
                "votes": o.votes,
                "question": o.question.question_en,
            }
            for o in options.order_by("question__display_order", "display_order")
        ]
        return {"scores": scores, "winners": [], "turnout": turnout, "mode": "choice"}

    n = election.total_seats or 1
    candidates = list(
        election.candidates.filter(is_active=True).select_related("member")
    )
    scores = {str(c.pk): 0 for c in candidates}
    names = {str(c.pk): c.name for c in candidates}
    founder_flags = {str(c.pk): bool(c.is_founder_candidate) for c in candidates}

    prefs = ElectionBallotPreference.objects.filter(
        ballot__election=election
    ).values_list("candidate_id", "rank")
    for candidate_id, rank in prefs:
        key = str(candidate_id)
        if key in scores:
            scores[key] += n - rank + 1

    ranked = sorted(
        scores.items(),
        key=lambda item: (-item[1], names[item[0]].lower()),
    )

    winners = []
    if election.election_type == ElectionType.ADVISORY_COUNCIL:
        reserved = founder_reserved_seats(election.total_seats)
        elected = elected_seats(election.total_seats)
        selected = set()
        for cid, pts in ranked:
            if len([w for w in winners if w["seat_type"] == "founder_reserved"]) >= reserved:
                break
            if founder_flags.get(cid):
                winners.append(
                    {
                        "candidate_id": cid,
                        "name": names[cid],
                        "points": pts,
                        "is_founder": True,
                        "seat_type": "founder_reserved",
                    }
                )
                selected.add(cid)
        for cid, pts in ranked:
            if len([w for w in winners if w["seat_type"] == "elected"]) >= elected:
                break
            if cid in selected:
                continue
            winners.append(
                {
                    "candidate_id": cid,
                    "name": names[cid],
                    "points": pts,
                    "is_founder": founder_flags.get(cid, False),
                    "seat_type": "elected",
                }
            )
            selected.add(cid)
    else:
        for cid, pts in ranked[: election.total_seats]:
            winners.append(
                {
                    "candidate_id": cid,
                    "name": names[cid],
                    "points": pts,
                    "is_founder": founder_flags.get(cid, False),
                    "seat_type": "elected",
                }
            )

    return {
        "scores": [
            {
                "candidate_id": cid,
                "name": names[cid],
                "points": pts,
                "is_founder": founder_flags.get(cid, False),
            }
            for cid, pts in ranked
        ],
        "winners": winners,
        "turnout": turnout,
        "mode": "ranked",
    }


def preview_stats(election: Election) -> dict:
    members = list(eligible_members_qs(election))
    founders = [m for m in members if is_founder_member(m)]
    return {
        "eligible_count": len(members),
        "founder_count": len(founders),
        "quorum_required": math.ceil(len(members) * election.quorum_ratio)
        if members
        else 0,
        "reserved_founder_seats": founder_reserved_seats(election.total_seats)
        if election.election_type == ElectionType.ADVISORY_COUNCIL
        else 0,
        "elected_seats": elected_seats(election.total_seats)
        if election.election_type == ElectionType.ADVISORY_COUNCIL
        else election.total_seats,
    }
