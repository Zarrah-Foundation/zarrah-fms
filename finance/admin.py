from django.contrib import admin

from finance.models import Expense, FinancialSummary, Income, MonthlyFinancialSummary


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "amount", "category", "expense_date", "approved_by")
    list_filter = ("category",)
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("title", "amount", "source", "received_date", "idempotency_key")
    search_fields = ("title", "description", "source", "idempotency_key")
    readonly_fields = ("created_at", "updated_at", "idempotency_key")

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        # Automated payment postings must not be silently mutated.
        if obj and obj.idempotency_key and (
            obj.idempotency_key.startswith("donation:")
            or obj.idempotency_key.startswith("membership-fee-payment:")
            or obj.idempotency_key.startswith("membership-registration-fee:")
        ):
            fields = list(
                dict.fromkeys(
                    fields
                    + ["title", "description", "amount", "received_date", "source"]
                )
            )
        return fields


@admin.register(FinancialSummary)
class FinancialSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "total_income",
        "total_expense",
        "net_balance",
        "is_published",
        "updated_at",
    )
    list_filter = ("is_published",)
    search_fields = ("year", "notes")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "year",
                    "total_income",
                    "total_expense",
                    "net_balance",
                    "notes",
                    "is_published",
                    "updated_at",
                ),
                "description": (
                    "Public financial transparency summaries only. "
                    "Do not enter private ledger or accounting detail here."
                ),
            },
        ),
    )


@admin.register(MonthlyFinancialSummary)
class MonthlyFinancialSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "year",
        "month",
        "total_income",
        "total_expense",
        "net_balance",
        "is_published",
    )
    list_filter = ("year", "is_published")
    readonly_fields = ("created_at", "updated_at")
