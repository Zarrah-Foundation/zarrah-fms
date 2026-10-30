"""Agenda ordering and proceedings HTML sanitization."""

from django.test import TestCase

from governance.services.agenda import add_agenda_item, reorder_agenda, save_proceedings
from governance.tests.helpers import create_meeting


class AgendaProceedingsTests(TestCase):
    def setUp(self):
        self.meeting = create_meeting()

    def test_agenda_auto_numbering_and_order(self):
        first = add_agenda_item(self.meeting, title_bn="প্রথম")
        second = add_agenda_item(self.meeting, title_bn="দ্বিতীয়")
        third = add_agenda_item(self.meeting, title_bn="তৃতীয়")

        self.assertEqual(first.number, 1)
        self.assertEqual(second.number, 2)
        self.assertEqual(third.number, 3)
        self.assertEqual(first.display_order, 1)
        self.assertEqual(second.display_order, 2)

    def test_reorder_agenda_updates_number_and_display_order(self):
        a = add_agenda_item(self.meeting, title_bn="A")
        b = add_agenda_item(self.meeting, title_bn="B")
        c = add_agenda_item(self.meeting, title_bn="C")

        reorder_agenda(self.meeting, [c.pk, a.pk, b.pk])
        ordered = list(self.meeting.agenda_items.order_by("display_order"))
        self.assertEqual([i.title_bn for i in ordered], ["C", "A", "B"])
        self.assertEqual([i.number for i in ordered], [1, 2, 3])

    def test_reorder_rejects_foreign_items(self):
        other_meeting = create_meeting(title_en="Other")
        item = add_agenda_item(other_meeting, title_bn="Foreign")
        local = add_agenda_item(self.meeting, title_bn="Local")
        with self.assertRaises(ValueError):
            reorder_agenda(self.meeting, [local.pk, item.pk])

    def test_proceedings_strips_script_tags(self):
        malicious = (
            "<p>Minutes recorded.</p>"
            "<script>alert('xss')</script>"
            "<p>More notes</p>"
        )
        proceeding = save_proceedings(
            self.meeting,
            content_bn=malicious,
            content_en="<script>evil()</script><p>English notes</p>",
        )
        self.assertNotIn("<script", proceeding.content_bn.lower())
        self.assertIn("Minutes recorded", proceeding.content_bn)
        self.assertNotIn("<script", proceeding.content_en.lower())
        self.assertIn("English notes", proceeding.content_en)
