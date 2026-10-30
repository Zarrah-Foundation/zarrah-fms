from datetime import datetime

from django.test import TestCase
from django.utils import timezone

from finance.models import Income, MonthlyFinancialSummary


class FinanceSummaryTests(TestCase):
    def test_moving_income_recomputes_the_old_month(self):
        tz = timezone.get_current_timezone()
        income = Income.objects.create(
            title="Grant",
            amount=100,
            received_date=timezone.make_aware(datetime(2026, 1, 15, 12, 0), tz),
            source="Grant",
        )
        january = MonthlyFinancialSummary.objects.get(year=2026, month=1)
        self.assertEqual(january.total_income, 100)

        income.received_date = timezone.make_aware(datetime(2026, 3, 2, 12, 0), tz)
        income.save()

        january.refresh_from_db()
        march = MonthlyFinancialSummary.objects.get(year=2026, month=3)
        self.assertEqual(january.total_income, 0)
        self.assertEqual(march.total_income, 100)
