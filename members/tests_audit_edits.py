"""Structured field edits: sensitive reason rules and immutable history."""

from django.test import TestCase

from audit.models import ActivityLog
from governance.tests.helpers import create_approved_member, create_staff_with_permission
from members.audit_edits import (
    SENSITIVE_MEMBER_FIELDS,
    apply_model_edits,
    compute_field_diffs,
    requires_reason,
)
from members.models import Member


class AuditEditsTests(TestCase):
    def setUp(self):
        self.actor = create_staff_with_permission(
            "audit-edit@example.com", "members.edit_sensitive"
        )
        self.user, self.member = create_approved_member(921)
        self.member.first_name = "Original"
        self.member.phone = "01710000921"
        self.member.occupation = "Teacher"
        self.member.save()

    def test_minor_field_ok_without_reason(self):
        apply_model_edits(
            self.member,
            {"occupation": "Engineer"},
            actor=self.actor,
            entity="Member",
            reason="",
            fields=["occupation"],
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.occupation, "Engineer")
        log = ActivityLog.objects.filter(
            entity="Member", entity_id=str(self.member.pk), action="FIELD_EDIT"
        ).latest("created_at")
        self.assertEqual(log.new_values.get("occupation"), "Engineer")

    def test_sensitive_requires_reason(self):
        with self.assertRaises(ValueError):
            apply_model_edits(
                self.member,
                {"first_name": "Changed"},
                actor=self.actor,
                entity="Member",
                reason="",
                fields=["first_name"],
            )
        self.member.refresh_from_db()
        self.assertEqual(self.member.first_name, "Original")

    def test_sensitive_with_reason_succeeds(self):
        apply_model_edits(
            self.member,
            {"first_name": "Updated"},
            actor=self.actor,
            entity="Member",
            reason="Legal name correction after NID verification.",
            fields=["first_name"],
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.first_name, "Updated")
        log = ActivityLog.objects.filter(
            entity="Member", entity_id=str(self.member.pk), action="FIELD_EDIT"
        ).latest("created_at")
        self.assertIn("NID", log.reason)
        self.assertEqual(log.old_values.get("first_name"), "Original")
        self.assertEqual(log.new_values.get("first_name"), "Updated")

    def test_history_values_immutable_after_write(self):
        apply_model_edits(
            self.member,
            {"phone": "01719999888"},
            actor=self.actor,
            entity="Member",
            reason="",
            fields=["phone"],
        )
        log = ActivityLog.objects.filter(
            entity="Member", entity_id=str(self.member.pk), action="FIELD_EDIT"
        ).latest("created_at")
        stored_old = dict(log.old_values)
        stored_new = dict(log.new_values)
        # Mutating the live member must not alter the logged snapshot.
        Member.objects.filter(pk=self.member.pk).update(phone="01710000000")
        log.refresh_from_db()
        self.assertEqual(log.old_values, stored_old)
        self.assertEqual(log.new_values, stored_new)

    def test_requires_reason_helper(self):
        diffs = compute_field_diffs(
            self.member, {"first_name": "X", "phone": "0171"}, ["first_name", "phone"]
        )
        self.assertTrue(requires_reason(diffs, SENSITIVE_MEMBER_FIELDS))
        diffs_minor = compute_field_diffs(
            self.member, {"phone": "01719999111"}, ["phone"]
        )
        self.assertFalse(requires_reason(diffs_minor, SENSITIVE_MEMBER_FIELDS))
