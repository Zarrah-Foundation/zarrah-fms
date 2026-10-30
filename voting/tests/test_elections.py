"""Phase 5 election engine tests — Advisory Council, freeze, choice ballots, secrecy."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from members.models import (
    Member,
    MemberGroup,
    MemberGroupMembership,
    MembershipType,
    MemberStatus,
)
from voting.models import (
    Election,
    ElectionAdminAction,
    ElectionBallot,
    ElectionCandidate,
    ElectionElectorate,
    ElectionOption,
    ElectionParticipation,
    ElectionQuestion,
    ElectionStatus,
    ElectionType,
    EligibilityMode,
)
from voting.services import (
    ElectionError,
    cancel_election,
    candidates_for_voter,
    cast_choice_ballot,
    cast_ranked_ballot,
    close_election,
    compute_results,
    elected_seats,
    extend_election,
    finalize_election,
    founder_reserved_seats,
    frozen_electorate_count,
    is_founder_member,
    open_election,
    publish_results,
    quorum_required,
    required_ranks_for_voter,
    restart_election,
    schedule_election,
    turnout_met,
)

User = get_user_model()


def _make_member(i, *, status=MemberStatus.APPROVED, founder=False, mtype=None):
    user = User.objects.create_user(email=f"voter{i}@example.com", password="pass12345")
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    member = Member.objects.create(
        member_id=f"M{i:04d}",
        user=user,
        first_name=f"Voter{i}",
        last_name="Test",
        phone=f"01700000{i:03d}",
        present_address="Dhaka",
        district="Dhaka",
        status=status,
        membership_type=mtype,
        is_founder=founder,
    )
    return user, member


class SeatMathTests(TestCase):
    def test_founder_reserved_seats(self):
        self.assertEqual(founder_reserved_seats(5), 3)
        self.assertEqual(founder_reserved_seats(6), 3)
        self.assertEqual(founder_reserved_seats(1), 1)
        self.assertEqual(elected_seats(5), 2)
        self.assertEqual(elected_seats(6), 3)


class AdvisoryCouncilElectionTests(TestCase):
    def setUp(self):
        self.founder_type = MembershipType.objects.create(
            name_en="Founder", name_bn="প্রতিষ্ঠাতা", slug="founder", fee_amount=0
        )
        self.regular_type = MembershipType.objects.create(
            name_en="General", name_bn="সাধারণ", slug="general", fee_amount=100
        )
        self.users = []
        self.members = []
        for i in range(6):
            user, member = _make_member(
                i,
                founder=i < 2,
                mtype=self.founder_type if i < 2 else self.regular_type,
            )
            self.users.append(user)
            self.members.append(member)

        self.election = Election.objects.create(
            title_en="Advisory Council 2026",
            title_bn="উপদেষ্টা পরিষদ ২০২৬",
            election_type=ElectionType.ADVISORY_COUNCIL,
            status=ElectionStatus.DRAFT,
            total_seats=4,
            quorum_numerator=2,
            quorum_denominator=3,
            allow_self_vote=False,
            auto_candidates=True,
            window_hours=48,
            created_by=self.users[0],
        )

    def _candidate_for(self, member):
        return ElectionCandidate.objects.get(election=self.election, member=member)

    def _rank_for(self, voter_user, exclude_extra=None):
        """Build a valid ranking excluding self (and optional extras)."""
        available = candidates_for_voter(self.election, voter_user)
        required = required_ranks_for_voter(self.election, voter_user)
        ids = [c.pk for c in available]
        if exclude_extra:
            ids = [i for i in ids if i not in exclude_extra]
        return ids[:required]

    def test_approved_eligible_non_approved_excluded(self):
        open_election(self.election, actor=self.users[0])
        self.assertEqual(frozen_electorate_count(self.election), 6)
        pending_user, _ = _make_member(99, status=MemberStatus.PENDING, mtype=self.regular_type)
        with self.assertRaises(ElectionError):
            cast_ranked_ballot(self.election, pending_user, self._rank_for(self.users[0]))

    def test_suspended_excluded(self):
        self.members[5].status = MemberStatus.SUSPENDED
        self.members[5].save(update_fields=["status"])
        open_election(self.election, actor=self.users[0])
        self.assertEqual(frozen_electorate_count(self.election), 5)
        with self.assertRaises(ElectionError):
            cast_ranked_ballot(self.election, self.users[5], [])

    def test_auto_candidates_at_open_no_nomination(self):
        self.assertEqual(self.election.candidates.count(), 0)
        open_election(self.election, actor=self.users[0])
        self.assertEqual(self.election.candidates.filter(is_active=True).count(), 6)
        for m in self.members:
            self.assertTrue(
                ElectionCandidate.objects.filter(
                    election=self.election, member=m, is_active=True
                ).exists()
            )

    def test_late_approved_excluded_after_freeze(self):
        open_election(self.election, actor=self.users[0])
        frozen = frozen_electorate_count(self.election)
        _make_member(50, status=MemberStatus.APPROVED, mtype=self.regular_type)
        self.assertEqual(frozen_electorate_count(self.election), frozen)
        self.assertEqual(self.election.candidates.filter(is_active=True).count(), 6)

    def test_candidates_locked_after_first_ballot(self):
        open_election(self.election, actor=self.users[0])
        cast_ranked_ballot(self.election, self.users[0], self._rank_for(self.users[0]))
        self.election.refresh_from_db()
        self.assertTrue(self.election.candidates_locked)

    def test_self_vote_hidden_and_server_rejected(self):
        open_election(self.election, actor=self.users[0])
        available = candidates_for_voter(self.election, self.users[0])
        own = self._candidate_for(self.members[0])
        self.assertNotIn(own, available)
        # Crafted request including self
        others = [c.pk for c in available[:3]]
        with self.assertRaises(ElectionError):
            cast_ranked_ballot(self.election, self.users[0], [own.pk] + others)

    def test_required_ranks_excludes_self(self):
        open_election(self.election, actor=self.users[0])
        # 6 candidates, seats=4, excluding self → 5 available → required = min(4,5)=4
        self.assertEqual(required_ranks_for_voter(self.election, self.users[0]), 4)
        # Shrink seats to 5 with only 5 others → still 5? seats 4.
        self.election.total_seats = 5
        self.election.save(update_fields=["total_seats"])
        # available excluding self = 5, seats=5 → required 5
        self.assertEqual(required_ranks_for_voter(self.election, self.users[0]), 5)

    def test_borda_scoring(self):
        open_election(self.election, actor=self.users[0])
        order = self._rank_for(self.users[5])
        cast_ranked_ballot(self.election, self.users[5], order)
        results = compute_results(self.election)
        by_id = {row["candidate_id"]: row["points"] for row in results["scores"]}
        n = 4
        for rank, cid in enumerate(order, start=1):
            self.assertEqual(by_id[str(cid)], n - rank + 1)

    def test_founder_reserved_no_duplicate_seats(self):
        open_election(self.election, actor=self.users[0])
        cast_ranked_ballot(self.election, self.users[5], self._rank_for(self.users[5]))
        results = compute_results(self.election)
        reserved = [w for w in results["winners"] if w["seat_type"] == "founder_reserved"]
        elected = [w for w in results["winners"] if w["seat_type"] == "elected"]
        self.assertEqual(len(reserved), founder_reserved_seats(4))
        self.assertTrue(all(w["is_founder"] for w in reserved))
        self.assertEqual(len(elected), elected_seats(4))
        winner_ids = [w["candidate_id"] for w in results["winners"]]
        self.assertEqual(len(winner_ids), len(set(winner_ids)))

    def test_advisory_48h_window(self):
        open_election(self.election, actor=self.users[0])
        self.election.refresh_from_db()
        self.assertEqual(self.election.end_at - self.election.start_at, timedelta(hours=48))

    def test_quorum_uses_frozen_electorate(self):
        open_election(self.election, actor=self.users[0])
        # 6 eligible → ceil(6*2/3)=4
        self.assertEqual(quorum_required(self.election), 4)
        _make_member(80, status=MemberStatus.APPROVED, mtype=self.regular_type)
        self.assertEqual(quorum_required(self.election), 4)
        self.assertFalse(turnout_met(self.election))
        for u in self.users[:4]:
            cast_ranked_ballot(self.election, u, self._rank_for(u))
        self.assertTrue(turnout_met(self.election))

    def test_finalize_blocked_without_quorum_override_audited(self):
        open_election(self.election, actor=self.users[0])
        close_election(self.election, actor=self.users[0])
        with self.assertRaises(ElectionError):
            finalize_election(self.election, actor=self.users[0])
        with self.assertRaises(ElectionError):
            finalize_election(
                self.election, actor=self.users[0], admin_override=True, notes=""
            )
        finalize_election(
            self.election,
            actor=self.users[0],
            admin_override=True,
            notes="Emergency constitutional override",
        )
        self.assertTrue(
            ElectionAdminAction.objects.filter(
                election=self.election, action="FINALIZE"
            ).exists()
        )

    def test_lifecycle_schedule_extend_restart_cancel_publish(self):
        schedule_election(self.election, actor=self.users[0])
        self.election.refresh_from_db()
        self.assertEqual(self.election.status, ElectionStatus.SCHEDULED)
        open_election(self.election, actor=self.users[0])
        new_end = timezone.now() + timedelta(hours=72)
        extend_election(self.election, new_end, actor=self.users[0])
        close_election(self.election, actor=self.users[0])
        finalize_election(
            self.election,
            actor=self.users[0],
            admin_override=True,
            notes="test",
        )
        publish_results(self.election, actor=self.users[0])
        self.election.refresh_from_db()
        self.assertTrue(self.election.results_published)

        e2 = Election.objects.create(
            title_en="Restart me",
            election_type=ElectionType.ADVISORY_COUNCIL,
            total_seats=3,
            auto_candidates=True,
        )
        open_election(e2, actor=self.users[0])
        avail = [c.pk for c in candidates_for_voter(e2, self.users[1])]
        req = required_ranks_for_voter(e2, self.users[1])
        cast_ranked_ballot(e2, self.users[1], avail[:req])
        close_election(e2, actor=self.users[0])
        with self.assertRaises(ElectionError):
            restart_election(e2, actor=self.users[0], confirm=False)
        restart_election(e2, actor=self.users[0], confirm=True)
        e2.refresh_from_db()
        self.assertEqual(e2.status, ElectionStatus.DRAFT)
        self.assertEqual(e2.ballots.count(), 0)
        self.assertEqual(e2.participations.count(), 0)
        self.assertIsNone(e2.electorate_frozen_at)

        e3 = Election.objects.create(
            title_en="Cancel me",
            election_type=ElectionType.GENERAL,
            total_seats=1,
        )
        cancel_election(e3, actor=self.users[0], notes="not needed")
        e3.refresh_from_db()
        self.assertEqual(e3.status, ElectionStatus.CANCELLED)

    def test_soft_close_rejects_votes(self):
        open_election(self.election, actor=self.users[0])
        self.election.end_at = timezone.now() - timedelta(seconds=1)
        self.election.save(update_fields=["end_at"])
        with self.assertRaises(ElectionError):
            cast_ranked_ballot(self.election, self.users[0], self._rank_for(self.users[0]))
        self.election.refresh_from_db()
        self.assertEqual(self.election.status, ElectionStatus.CLOSED)

    def test_ballot_secrecy_no_user_fk(self):
        open_election(self.election, actor=self.users[0])
        ballot = cast_ranked_ballot(
            self.election, self.users[0], self._rank_for(self.users[0])
        )
        self.assertFalse(any(f.name == "user" for f in ElectionBallot._meta.fields))
        self.assertTrue(
            ElectionParticipation.objects.filter(
                election=self.election, user=self.users[0]
            ).exists()
        )
        self.assertIsNotNone(ballot.ballot_token)

    def test_is_founder_member_helpers(self):
        self.assertTrue(is_founder_member(self.members[0]))
        self.assertFalse(is_founder_member(self.members[3]))
        self.members[3].is_founder = False
        self.members[3].membership_type = self.founder_type
        self.members[3].save()
        self.assertTrue(is_founder_member(self.members[3]))


class EligibilityModeTests(TestCase):
    def setUp(self):
        self.t_a = MembershipType.objects.create(
            name_en="Type A", slug="type-a", fee_amount=0
        )
        self.t_b = MembershipType.objects.create(
            name_en="Type B", slug="type-b", fee_amount=0
        )
        self.users = []
        self.members = []
        for i, mt in enumerate([self.t_a, self.t_a, self.t_b]):
            u, m = _make_member(i + 100, mtype=mt)
            self.users.append(u)
            self.members.append(m)
        self.group = MemberGroup.objects.create(name_en="Council", slug="council")
        MemberGroupMembership.objects.create(group=self.group, member=self.members[0])
        MemberGroupMembership.objects.create(group=self.group, member=self.members[2])

    def test_by_membership_types(self):
        election = Election.objects.create(
            title_en="Type filter",
            election_type=ElectionType.GENERAL,
            total_seats=1,
            eligibility_mode=EligibilityMode.BY_MEMBERSHIP_TYPES,
            auto_candidates=True,
            allow_self_vote=False,
        )
        election.membership_types.add(self.t_a)
        open_election(election)
        self.assertEqual(frozen_electorate_count(election), 2)
        # members[2] is type B
        with self.assertRaises(ElectionError):
            cast_ranked_ballot(
                election,
                self.users[2],
                [c.pk for c in candidates_for_voter(election, self.users[2])[:1]],
            )

    def test_by_groups(self):
        election = Election.objects.create(
            title_en="Group filter",
            election_type=ElectionType.GENERAL,
            total_seats=1,
            eligibility_mode=EligibilityMode.BY_GROUPS,
            auto_candidates=True,
            allow_self_vote=False,
        )
        election.member_groups.add(self.group)
        open_election(election)
        self.assertEqual(frozen_electorate_count(election), 2)
        self.assertTrue(
            ElectionElectorate.objects.filter(
                election=election, user=self.users[0]
            ).exists()
        )
        self.assertFalse(
            ElectionElectorate.objects.filter(
                election=election, user=self.users[1]
            ).exists()
        )


class ChoiceElectionTests(TestCase):
    def setUp(self):
        self.users = []
        self.members = []
        for i in range(3):
            u, m = _make_member(i + 200)
            self.users.append(u)
            self.members.append(m)

    def test_yes_no_tally_and_quorum(self):
        election = Election.objects.create(
            title_en="Approve proposal?",
            election_type=ElectionType.YES_NO,
            quorum_numerator=2,
            quorum_denominator=3,
        )
        ElectionQuestion.objects.create(
            election=election, question_en="Do you approve?", display_order=0
        )
        open_election(election)
        opts = list(
            ElectionOption.objects.filter(question__election=election).order_by(
                "display_order"
            )
        )
        self.assertEqual(len(opts), 2)
        cast_choice_ballot(election, self.users[0], [opts[0].pk])
        cast_choice_ballot(election, self.users[1], [opts[0].pk])
        with self.assertRaises(ElectionError):
            cast_choice_ballot(election, self.users[0], [opts[1].pk])
        results = compute_results(election)
        self.assertEqual(results["mode"], "choice")
        yes_row = next(r for r in results["scores"] if r["label"] == "Yes")
        self.assertEqual(yes_row["votes"], 2)
        # quorum ceil(3*2/3)=2
        self.assertTrue(turnout_met(election))
        close_election(election)
        finalize_election(election)
        publish_results(election)
        self.assertTrue(election.results_published)

    def test_multi_choice_single_and_multiple(self):
        election = Election.objects.create(
            title_en="Pick options",
            election_type=ElectionType.MULTI_CHOICE,
            allow_multiple_selections=True,
            max_selections=2,
        )
        q = ElectionQuestion.objects.create(
            election=election, question_en="Which?", display_order=0
        )
        o1 = ElectionOption.objects.create(question=q, label_en="Alpha", display_order=0)
        o2 = ElectionOption.objects.create(question=q, label_en="Beta", display_order=1)
        o3 = ElectionOption.objects.create(question=q, label_en="Gamma", display_order=2)
        open_election(election)
        cast_choice_ballot(election, self.users[0], [o1.pk, o2.pk])
        with self.assertRaises(ElectionError):
            cast_choice_ballot(election, self.users[1], [o1.pk, o2.pk, o3.pk])
        election.allow_multiple_selections = False
        election.max_selections = 1
        election.save()
        cast_choice_ballot(election, self.users[1], [o3.pk])
        results = compute_results(election)
        by_label = {r["label"]: r["votes"] for r in results["scores"]}
        self.assertEqual(by_label["Alpha"], 1)
        self.assertEqual(by_label["Beta"], 1)
        self.assertEqual(by_label["Gamma"], 1)


class ElectionSecurityViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.founder_type = MembershipType.objects.create(
            name_en="Founder", slug="founder-sec", fee_amount=0
        )
        self.users = []
        self.members = []
        for i in range(4):
            u, m = _make_member(i + 300, founder=i == 0, mtype=self.founder_type)
            self.users.append(u)
            self.members.append(m)
        self.election = Election.objects.create(
            title_en="Security AC",
            election_type=ElectionType.ADVISORY_COUNCIL,
            total_seats=2,
            auto_candidates=True,
            allow_self_vote=False,
        )
        open_election(self.election)

    def test_member_cast_and_duplicate(self):
        self.client.force_login(self.users[0])
        url = reverse("my-election-cast", kwargs={"pk": self.election.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        own = ElectionCandidate.objects.get(
            election=self.election, member=self.members[0]
        )
        # Own candidate UUID must not appear as a selectable option value
        self.assertNotContains(resp, f'value="{own.pk}"')
        available = candidates_for_voter(self.election, self.users[0])
        required = required_ranks_for_voter(self.election, self.users[0])
        data = {f"rank_{i}": str(available[i - 1].pk) for i in range(1, required + 1)}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            ElectionParticipation.objects.filter(
                election=self.election, user=self.users[0]
            ).count(),
            1,
        )

    def test_unpublished_results_blocked(self):
        self.client.force_login(self.users[0])
        url = reverse("my-election-results", kwargs={"pk": self.election.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_legacy_voting_redirects(self):
        self.client.force_login(self.users[0])
        resp = self.client.get(reverse("voting-list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard/my-elections/", resp.url)

    def test_cannot_vote_wrong_election_candidates(self):
        other = Election.objects.create(
            title_en="Other",
            election_type=ElectionType.ADVISORY_COUNCIL,
            total_seats=2,
            auto_candidates=True,
        )
        open_election(other)
        foreign = ElectionCandidate.objects.filter(election=other).first()
        with self.assertRaises(ElectionError):
            cast_ranked_ballot(
                self.election,
                self.users[1],
                [foreign.pk]
                + [
                    c.pk
                    for c in candidates_for_voter(self.election, self.users[1])[
                        : required_ranks_for_voter(self.election, self.users[1]) - 1
                    ]
                ],
            )
