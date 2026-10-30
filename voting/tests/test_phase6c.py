"""Phase 6C — Advisory Council quorum hard-lock, RBAC, secrecy regression."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role as LegacyRole
from members.models import Member, MembershipType, MemberStatus
from rbac.models import Permission, Role, RolePermission
from rbac.permissions import has_action
from voting.forms import ElectionForm
from voting.models import (
    Election,
    ElectionBallot,
    ElectionStatus,
    ElectionType,
    EligibilityMode,
)
from voting.services import (
    ElectionError,
    apply_advisory_council_constitution,
    cast_ranked_ballot,
    close_election,
    effective_quorum_ratio,
    finalize_election,
    open_election,
    quorum_required,
    required_ranks_for_voter,
    turnout_met,
)

User = get_user_model()


def _member(i, *, status=MemberStatus.APPROVED, mtype=None):
    user = User.objects.create_user(email=f"p6c{i}@example.com", password="pass12345")
    user.email_verified = timezone.now()
    user.save(update_fields=["email_verified"])
    member = Member.objects.create(
        member_id=f"P6C{i:04d}",
        user=user,
        first_name=f"P{i}",
        last_name="SixC",
        phone=f"01800000{i:03d}",
        present_address="Dhaka",
        district="Dhaka",
        status=status,
        membership_type=mtype,
    )
    return user, member


class AdvisoryCouncilQuorumHardLockTests(TestCase):
    def setUp(self):
        self.mtype = MembershipType.objects.create(
            name_en="General", name_bn="সাধারণ", slug="general-p6c", fee_amount=50
        )
        self.users = []
        self.members = []
        for i in range(6):
            u, m = _member(i, mtype=self.mtype)
            self.users.append(u)
            self.members.append(m)
        self.election = Election.objects.create(
            title_en="AC 6C",
            title_bn="AC 6C",
            election_type=ElectionType.ADVISORY_COUNCIL,
            total_seats=4,
            start_at=timezone.now(),
            quorum_numerator=1,
            quorum_denominator=2,
            window_hours=24,
            allow_self_vote=True,
            auto_candidates=False,
            eligibility_mode=EligibilityMode.BY_MEMBERSHIP_TYPES,
            status=ElectionStatus.DRAFT,
            created_by=self.users[0],
        )

    def test_form_clean_forces_two_thirds_and_48h(self):
        form = ElectionForm(
            data={
                "title_bn": "AC",
                "title_en": "AC",
                "description_bn": "",
                "description_en": "",
                "election_type": ElectionType.ADVISORY_COUNCIL,
                "start_at": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                "window_hours": 12,
                "total_seats": 4,
                "quorum_numerator": 1,
                "quorum_denominator": 2,
                "allow_self_vote": True,
                "auto_candidates": False,
                "eligibility_mode": EligibilityMode.BY_MEMBERSHIP_TYPES,
                "allow_multiple_selections": False,
                "max_selections": 1,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["quorum_numerator"], 2)
        self.assertEqual(form.cleaned_data["quorum_denominator"], 3)
        self.assertEqual(form.cleaned_data["window_hours"], 48)
        self.assertFalse(form.cleaned_data["allow_self_vote"])
        self.assertTrue(form.cleaned_data["auto_candidates"])
        self.assertEqual(
            form.cleaned_data["eligibility_mode"], EligibilityMode.ALL_APPROVED
        )

    def test_open_forces_constitution_and_runtime_ratio(self):
        open_election(self.election, actor=self.users[0])
        self.election.refresh_from_db()
        self.assertEqual(self.election.quorum_numerator, 2)
        self.assertEqual(self.election.quorum_denominator, 3)
        self.assertEqual(self.election.window_hours, 48)
        self.assertEqual(
            self.election.end_at - self.election.start_at, timedelta(hours=48)
        )
        self.assertAlmostEqual(effective_quorum_ratio(self.election), 2 / 3)
        # 6 eligible → ceil(6*2/3)=4, not ceil(6*1/2)=3
        self.assertEqual(quorum_required(self.election), 4)

    def test_saved_half_quorum_cannot_weaken_runtime(self):
        # Even if DB somehow stores 1/2 after open, runtime still uses 2/3.
        open_election(self.election, actor=self.users[0])
        Election.objects.filter(pk=self.election.pk).update(
            quorum_numerator=1, quorum_denominator=2
        )
        self.election.refresh_from_db()
        self.assertEqual(self.election.quorum_numerator, 1)
        self.assertEqual(quorum_required(self.election), 4)
        self.assertFalse(turnout_met(self.election))

    def test_two_thirds_reached_then_finalize(self):
        open_election(self.election, actor=self.users[0])
        from voting.services import candidates_for_voter

        for u in self.users[:4]:
            cands = list(candidates_for_voter(self.election, u))
            ranks = required_ranks_for_voter(self.election, u)
            ordered = [c.pk for c in cands[:ranks]]
            cast_ranked_ballot(self.election, u, ordered)
        self.assertTrue(turnout_met(self.election))
        close_election(self.election, actor=self.users[0])
        finalize_election(self.election, actor=self.users[0])
        self.election.refresh_from_db()
        self.assertEqual(self.election.status, ElectionStatus.FINALIZED)

    def test_below_two_thirds_blocks_finalize(self):
        open_election(self.election, actor=self.users[0])
        from voting.services import candidates_for_voter

        for u in self.users[:3]:
            cands = list(candidates_for_voter(self.election, u))
            ranks = required_ranks_for_voter(self.election, u)
            cast_ranked_ballot(self.election, u, [c.pk for c in cands[:ranks]])
        self.assertFalse(turnout_met(self.election))
        close_election(self.election, actor=self.users[0])
        with self.assertRaises(ElectionError):
            finalize_election(self.election, actor=self.users[0])

    def test_apply_helper_forces_fields(self):
        apply_advisory_council_constitution(self.election)
        self.assertEqual(self.election.quorum_numerator, 2)
        self.assertEqual(self.election.quorum_denominator, 3)
        self.assertEqual(self.election.window_hours, 48)


class AdvisoryCouncilEligibilityFreezeTests(TestCase):
    def setUp(self):
        self.mtype = MembershipType.objects.create(
            name_en="G", name_bn="গ", slug="g-p6c-el", fee_amount=50
        )
        self.users = []
        self.members = []
        for i in range(3):
            u, m = _member(100 + i, mtype=self.mtype)
            self.users.append(u)
            self.members.append(m)
        self.election = Election.objects.create(
            title_en="AC elig",
            title_bn="AC",
            election_type=ElectionType.ADVISORY_COUNCIL,
            total_seats=2,
            start_at=timezone.now(),
            status=ElectionStatus.DRAFT,
            created_by=self.users[0],
        )

    def test_member_is_voter_and_candidate_no_self_rank(self):
        from voting.models import ElectionCandidate, ElectionElectorate
        from voting.services import candidates_for_voter

        open_election(self.election, actor=self.users[0])
        self.assertEqual(ElectionElectorate.objects.filter(election=self.election).count(), 3)
        self.assertEqual(
            ElectionCandidate.objects.filter(election=self.election, is_active=True).count(),
            3,
        )
        voter = self.users[0]
        selectable = list(candidates_for_voter(self.election, voter))
        self.assertTrue(all(c.member_id != self.members[0].pk for c in selectable))
        self.assertEqual(len(selectable), 2)
        # Late approval does not join frozen electorate
        _member(999, mtype=self.mtype)
        from voting.services import frozen_electorate_count

        self.assertEqual(frozen_electorate_count(self.election), 3)


class ElectionSecrecyAndRBACTests(TestCase):
    def test_ballot_has_no_user_field(self):
        field_names = {f.name for f in ElectionBallot._meta.get_fields()}
        self.assertNotIn("user", field_names)
        self.assertNotIn("voter", field_names)
        self.assertNotIn("member", field_names)

    def test_hidden_ballot_admin_denies_access(self):
        from django.contrib.admin.sites import AdminSite
        from voting.admin import ElectionBallotAdmin

        admin_user = User.objects.create_superuser(
            email="sa-p6c@example.com", password="pass12345"
        )
        ma = ElectionBallotAdmin(ElectionBallot, AdminSite())
        req = type("R", (), {"user": admin_user})()
        self.assertFalse(ma.has_module_permission(req))
        self.assertFalse(ma.has_view_permission(req))
        self.assertFalse(ma.has_add_permission(req))

    def test_volunteer_coordinator_lacks_election_manage(self):
        # Mirror Phase 6C seed: VC must not administer elections.
        role, _ = Role.objects.get_or_create(
            name="Volunteer Coordinator",
            defaults={"is_system": True, "legacy_role": LegacyRole.VOLUNTEER_COORDINATOR},
        )
        RolePermission.objects.filter(role=role).delete()
        for code in ("dashboard.view", "volunteers.view", "notifications.view"):
            perm = Permission.objects.filter(codename=code).first()
            if perm:
                RolePermission.objects.get_or_create(role=role, permission=perm)
        user = User.objects.create_user(
            email="vc-p6c@example.com",
            password="pass12345",
            role=LegacyRole.VOLUNTEER_COORDINATOR,
        )
        # Legacy role maps to this Role; no elections.* grants remain.
        self.assertEqual(role.legacy_role, LegacyRole.VOLUNTEER_COORDINATOR)
        self.assertFalse(has_action(user, "elections", "manage"))
        self.assertFalse(has_action(user, "elections", "create"))
        self.assertFalse(has_action(user, "elections", "view"))

    def test_member_cannot_access_election_admin_list(self):
        user = User.objects.create_user(
            email="mem-p6c@example.com",
            password="pass12345",
            role=LegacyRole.MEMBER,
        )
        user.email_verified = timezone.now()
        user.save()
        client = Client()
        client.force_login(user)
        resp = client.get(reverse("dashboard-elections"))
        self.assertIn(resp.status_code, (302, 403))
