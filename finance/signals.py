from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from finance.models import Expense, FinancialSummary, Income, MonthlyFinancialSummary


def _recompute_year(year):
    total_income = (
        Income.objects.filter(received_date__year=year).aggregate(s=Sum("amount"))["s"] or 0
    )
    total_expense = (
        Expense.objects.filter(expense_date__year=year).aggregate(s=Sum("amount"))["s"] or 0
    )
    FinancialSummary.objects.update_or_create(
        year=year,
        defaults={
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": total_income - total_expense,
        },
    )


def _recompute_month(year, month):
    total_income = (
        Income.objects.filter(received_date__year=year, received_date__month=month).aggregate(
            s=Sum("amount")
        )["s"]
        or 0
    )
    total_expense = (
        Expense.objects.filter(expense_date__year=year, expense_date__month=month).aggregate(
            s=Sum("amount")
        )["s"]
        or 0
    )
    MonthlyFinancialSummary.objects.update_or_create(
        year=year,
        month=month,
        defaults={
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": total_income - total_expense,
        },
    )


def _get_dates_from_instance(instance):
    if isinstance(instance, Income):
        dt = instance.received_date
    else:
        dt = instance.expense_date
    return dt.year, dt.month


@receiver(post_save, sender=Income)
@receiver(post_save, sender=Expense)
def recompute_on_save(sender, instance, **kwargs):
    year, month = _get_dates_from_instance(instance)
    _recompute_year(year)
    _recompute_month(year, month)


@receiver(post_delete, sender=Income)
@receiver(post_delete, sender=Expense)
def recompute_on_delete(sender, instance, **kwargs):
    year, month = _get_dates_from_instance(instance)
    _recompute_year(year)
    _recompute_month(year, month)
