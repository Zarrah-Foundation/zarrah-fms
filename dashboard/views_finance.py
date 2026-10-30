"""Finance module: income, expense, balance overview, cash book, ledger."""

from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _l

from dashboard.crud import DashCreateView, DashDeleteView, DashListView, DashUpdateView
from dashboard.forms import ExpenseForm, IncomeForm
from finance.models import Expense, Income, MonthlyFinancialSummary
from rbac.permissions import has_action


def _require(request, action):
    return has_action(request.user, "finance", action)


@login_required
def finance_overview(request):
    if not _require(request, "view"):
        return redirect("dashboard")
    income_total = Income.objects.aggregate(s=Sum("amount"))["s"] or 0
    expense_total = Expense.objects.aggregate(s=Sum("amount"))["s"] or 0
    monthly = MonthlyFinancialSummary.objects.order_by("-year", "-month")[:12]
    return render(
        request,
        "dashboard/finance/overview.html",
        {
            "income_total": income_total,
            "expense_total": expense_total,
            "net_balance": income_total - expense_total,
            "monthly": monthly,
            "can_create": _require(request, "create"),
        },
    )


@login_required
def cash_book(request):
    if not _require(request, "view"):
        return redirect("dashboard")
    from django.core.paginator import Paginator
    from django.utils import timezone

    incomes = [
        {
            "date": i.received_date,
            "title": i.title,
            "type": "income",
            "amount": i.amount,
            "ref": i.source or "",
        }
        for i in Income.objects.order_by("received_date", "pk")
    ]
    expenses = [
        {
            "date": e.expense_date,
            "title": e.title,
            "type": "expense",
            "amount": e.amount,
            "ref": e.category or "",
        }
        for e in Expense.objects.order_by("expense_date", "pk")
    ]
    fallback = timezone.now()
    entries = sorted(chain(incomes, expenses), key=lambda x: (x["date"] or fallback, x["title"]))
    balance = 0
    for entry in entries:
        balance += entry["amount"] if entry["type"] == "income" else -entry["amount"]
        entry["balance"] = balance
    # Newest first for display; closing_balance is full-ledger.
    entries.reverse()
    page_obj = Paginator(entries, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/finance/cash_book.html",
        {
            "entries": page_obj,
            "page_obj": page_obj,
            "closing_balance": balance,
        },
    )


@login_required
def ledger(request):
    if not _require(request, "view"):
        return redirect("dashboard")
    income_by_source = (
        Income.objects.values("source").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
    )
    expense_by_category = (
        Expense.objects.values("category").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
    )
    return render(
        request,
        "dashboard/finance/ledger.html",
        {"income_by_source": income_by_source, "expense_by_category": expense_by_category},
    )


# ---- Income CRUD ----

class IncomeList(DashListView):
    model = Income
    permission_module = "finance"
    ordering = ["-received_date"]
    search_fields = ["title", "source"]
    page_title = _l("Income")
    page_icon = "bi-arrow-down-circle"
    columns = [
        {"label": _l("Title"), "field": "title"},
        {"label": _l("Source"), "field": "source"},
        {"label": _l("Amount"), "field": "amount"},
        {"label": _l("Date"), "field": "received_date"},
    ]
    create_url_name = "dashboard-income-create"
    edit_url_name = "dashboard-income-edit"
    delete_url_name = "dashboard-income-delete"


class IncomeCreate(DashCreateView):
    model = Income
    permission_module = "finance"
    form_class = IncomeForm
    page_title = _l("Add Income")
    success_url_name = "dashboard-finance-income"


class IncomeUpdate(DashUpdateView):
    model = Income
    permission_module = "finance"
    form_class = IncomeForm
    page_title = _l("Edit Income")
    success_url_name = "dashboard-finance-income"


class IncomeDelete(DashDeleteView):
    model = Income
    permission_module = "finance"
    success_url_name = "dashboard-finance-income"


# ---- Expense CRUD ----

class ExpenseList(DashListView):
    model = Expense
    permission_module = "finance"
    ordering = ["-expense_date"]
    search_fields = ["title", "category"]
    page_title = _l("Expenses")
    page_icon = "bi-arrow-up-circle"
    columns = [
        {"label": _l("Title"), "field": "title"},
        {"label": _l("Category"), "field": "category"},
        {"label": _l("Amount"), "field": "amount"},
        {"label": _l("Date"), "field": "expense_date"},
    ]
    create_url_name = "dashboard-expense-create"
    edit_url_name = "dashboard-expense-edit"
    delete_url_name = "dashboard-expense-delete"


class ExpenseCreate(DashCreateView):
    model = Expense
    permission_module = "finance"
    form_class = ExpenseForm
    page_title = _l("Add Expense")
    success_url_name = "dashboard-finance-expense"


class ExpenseUpdate(DashUpdateView):
    model = Expense
    permission_module = "finance"
    form_class = ExpenseForm
    page_title = _l("Edit Expense")
    success_url_name = "dashboard-finance-expense"


class ExpenseDelete(DashDeleteView):
    model = Expense
    permission_module = "finance"
    success_url_name = "dashboard-finance-expense"
