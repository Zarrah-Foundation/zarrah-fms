import uuid

from django.db import models
from django.utils import timezone


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(null=True, blank=True)
    amount = models.FloatField()
    expense_date = models.DateTimeField(default=timezone.now)
    category = models.CharField(max_length=100, null=True, blank=True)
    approved_by = models.CharField(max_length=200, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["expense_date"]),
        ]

    def __str__(self):
        return self.title


class Income(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(null=True, blank=True)
    amount = models.FloatField()
    received_date = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=200, null=True, blank=True)
    # Idempotency for automated postings (e.g. membership-fee-payment:<uuid>).
    idempotency_key = models.CharField(
        max_length=120, unique=True, null=True, blank=True, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["received_date"]),
        ]

    def __str__(self):
        return self.title


class FinancialSummary(models.Model):
    """Public yearly financial snapshot (not private ledger transactions)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.IntegerField(unique=True)
    total_income = models.FloatField(default=0)
    total_expense = models.FloatField(default=0)
    net_balance = models.FloatField(default=0)
    is_published = models.BooleanField(
        default=True,
        help_text="When unchecked, this yearly summary is hidden from the public Transparency page.",
    )
    notes = models.TextField(blank=True, default="", help_text="Optional public note for this year.")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Financial Summary {self.year}"


class MonthlyFinancialSummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year = models.IntegerField()
    month = models.IntegerField()
    total_income = models.FloatField(default=0)
    total_expense = models.FloatField(default=0)
    net_balance = models.FloatField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("year", "month")]
        indexes = [
            models.Index(fields=["year"]),
        ]

    def __str__(self):
        return f"{self.year}-{self.month:02d}"
