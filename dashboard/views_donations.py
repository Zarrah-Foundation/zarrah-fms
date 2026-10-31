"""Donations module: categories, quick amounts, payment methods, donations,
manual entry, and reports."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _, gettext_lazy as _l

from core.choices import DonationStatus
from dashboard.crud import DashCreateView, DashDeleteView, DashListView, DashUpdateView
from dashboard.forms import (
    DonationCategoryForm,
    DonationQuickAmountForm,
    ManualDonationForm,
    PaymentMethodConfigForm,
    SSLCommerzCredentialForm,
)
from donations.models import (
    Donation,
    DonationCategory,
    DonationQuickAmount,
    PaymentMethodConfig,
)
from donations.services import create_manual_donation
from rbac.permissions import has_action


def _require(request, module, action):
    return has_action(request.user, module, action)


# =========================================================================
# Donation Categories (CMS)
# =========================================================================

class CategoryList(DashListView):
    model = DonationCategory
    permission_module = "donation_categories"
    ordering = ["display_order", "name_en"]
    search_fields = ["name_en", "name_bn"]
    page_title = _l("Donation Categories")
    page_icon = "bi-tags"
    columns = [
        {"label": _l("Name"), "field": "name_en"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Featured"), "field": "is_featured"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-donation-category-create"
    edit_url_name = "dashboard-donation-category-edit"
    delete_url_name = "dashboard-donation-category-delete"


class CategoryCreate(DashCreateView):
    model = DonationCategory
    permission_module = "donation_categories"
    form_class = DonationCategoryForm
    page_title = _l("Add Donation Category")
    success_url_name = "dashboard-donation-categories"


class CategoryUpdate(DashUpdateView):
    model = DonationCategory
    permission_module = "donation_categories"
    form_class = DonationCategoryForm
    page_title = _l("Edit Donation Category")
    success_url_name = "dashboard-donation-categories"


class CategoryDelete(DashDeleteView):
    model = DonationCategory
    permission_module = "donation_categories"
    success_url_name = "dashboard-donation-categories"


# =========================================================================
# Quick Amounts (CMS)
# =========================================================================

class QuickAmountList(DashListView):
    model = DonationQuickAmount
    permission_module = "quick_amounts"
    ordering = ["category__name_en", "display_order", "amount"]
    page_title = _l("Quick Amounts")
    page_icon = "bi-coin"
    columns = [
        {"label": _l("Category"), "field": "category"},
        {"label": _l("Amount"), "field": "amount"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-quick-amount-create"
    edit_url_name = "dashboard-quick-amount-edit"
    delete_url_name = "dashboard-quick-amount-delete"

    def get_queryset(self):
        return super().get_queryset().select_related("category")


class QuickAmountCreate(DashCreateView):
    model = DonationQuickAmount
    permission_module = "quick_amounts"
    form_class = DonationQuickAmountForm
    page_title = _l("Add Quick Amount")
    success_url_name = "dashboard-quick-amounts"


class QuickAmountUpdate(DashUpdateView):
    model = DonationQuickAmount
    permission_module = "quick_amounts"
    form_class = DonationQuickAmountForm
    page_title = _l("Edit Quick Amount")
    success_url_name = "dashboard-quick-amounts"


class QuickAmountDelete(DashDeleteView):
    model = DonationQuickAmount
    permission_module = "quick_amounts"
    success_url_name = "dashboard-quick-amounts"


# =========================================================================
# Payment Methods (CMS)
# =========================================================================

class PaymentMethodList(DashListView):
    model = PaymentMethodConfig
    permission_module = "payment_methods"
    ordering = ["display_order", "method"]
    page_title = _l("Payment Methods")
    page_icon = "bi-credit-card"
    template_name = "dashboard/donations/payment_methods_list.html"
    columns = [
        {"label": _l("Method"), "field": "get_method_display"},
        {"label": _l("Display Name"), "field": "display_name"},
        {"label": _l("Enabled"), "field": "is_enabled"},
    ]
    create_url_name = "dashboard-payment-method-create"
    edit_url_name = "dashboard-payment-method-edit"
    delete_url_name = "dashboard-payment-method-delete"

    def get_context_data(self, **kwargs):
        from donations.gateway_capabilities import hosted_card_channels, method_capabilities

        ctx = super().get_context_data(**kwargs)
        rows = []
        for m in ctx["object_list"]:
            cap = method_capabilities(m.method)
            rows.append({"config": m, "cap": cap})
        ctx["method_rows"] = rows
        ctx["hosted_cards"] = hosted_card_channels()
        return ctx


class PaymentMethodCreate(DashCreateView):
    model = PaymentMethodConfig
    permission_module = "payment_methods"
    form_class = PaymentMethodConfigForm
    page_title = _l("Add Payment Method")
    success_url_name = "dashboard-payment-methods"


class PaymentMethodUpdate(DashUpdateView):
    model = PaymentMethodConfig
    permission_module = "payment_methods"
    form_class = PaymentMethodConfigForm
    page_title = _l("Edit Payment Method")
    success_url_name = "dashboard-payment-methods"


class PaymentMethodDelete(DashDeleteView):
    model = PaymentMethodConfig
    permission_module = "payment_methods"
    success_url_name = "dashboard-payment-methods"


@login_required
def payment_method_configure(request, pk):
    """Provider credential configuration — secrets never re-displayed after save."""
    if not _require(request, "payment_methods", "edit"):
        return redirect("dashboard")
    config = get_object_or_404(PaymentMethodConfig, pk=pk)
    from core.choices import PaymentMethod
    from dashboard.forms_payments import DirectProviderCredentialForm
    from donations.credential_service import public_credential_status
    from donations.payment_ops import log_payment_event
    from donations.provider_capabilities import all_provider_health

    if config.method == PaymentMethod.SSLCOMMERZ:
        form_cls = SSLCommerzCredentialForm
        template = "dashboard/donations/payment_method_configure.html"
        title = _("Configure SSLCommerz")
    elif config.method in (PaymentMethod.BKASH, PaymentMethod.NAGAD):
        form_cls = DirectProviderCredentialForm
        template = "dashboard/donations/payment_method_configure_direct.html"
        title = _("Configure %(name)s") % {"name": config.get_method_display()}
    else:
        messages.warning(
            request,
            _("Credential configuration is only available for SSLCommerz, bKash, and Nagad."),
        )
        return redirect("dashboard-payment-methods")

    if request.method == "POST":
        form = form_cls(request.POST, instance=config)
        if form.is_valid():
            form.save()
            log_payment_event(
                actor=request.user,
                action="payment_method_configured",
                provider=config.method,
                entity="PaymentMethodConfig",
                entity_id=str(config.pk),
                message=f"{config.method} configuration saved (secrets redacted)",
            )
            messages.success(request, _("Payment gateway configuration saved."))
            return redirect("dashboard-payment-method-configure", pk=config.pk)
    else:
        form = form_cls(instance=config)

    bkash_readiness = None
    if config.method == PaymentMethod.BKASH:
        from donations.bkash_config import bkash_readiness as bkash_readiness_fn

        bkash_readiness = bkash_readiness_fn()
    status = public_credential_status(config) if config.method == PaymentMethod.SSLCOMMERZ else {
        "configured": bool(config.api_app_key and config.encrypted_api_secret),
        "is_sandbox": config.is_sandbox,
        "source": "database" if config.api_app_key else "missing",
        "gateway_enabled": config.is_enabled,
        "last_test_status": config.last_test_status,
        "last_test_message": config.last_test_message,
        "has_saved_secret": bool(config.encrypted_api_secret),
        "store_id_masked": "",
    }
    health = next((h for h in all_provider_health() if h.method == config.method), None)
    return render(
        request,
        template,
        {
            "form": form,
            "config": config,
            "cred_status": status,
            "provider_health": health,
            "page_title": title,
            "live_validation_pending": True,
            "bkash_readiness": bkash_readiness,
        },
    )


@login_required
def payment_method_test_connection(request, pk):
    """POST-only safe credential test — no donations, fees, or finance mutations."""
    if request.method != "POST":
        return redirect("dashboard-payment-methods")
    if not _require(request, "payment_methods", "edit"):
        return redirect("dashboard")
    config = get_object_or_404(PaymentMethodConfig, pk=pk)
    from core.choices import PaymentMethod
    from donations.credential_service import test_sslcommerz_connection
    from django.http import JsonResponse

    if config.method == PaymentMethod.BKASH:
        from donations.bkash_config import test_bkash_connection

        status, message = test_bkash_connection()
        safe = {"ok": status == "SUCCESS", "status": status, "message": message}
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(safe)
        if status == "SUCCESS":
            messages.success(request, _("Sandbox connection test: SUCCESS — %(msg)s") % {"msg": message})
        elif status == "NOT_CONFIGURED":
            messages.warning(request, _("Connection test: NOT CONFIGURED — %(msg)s") % {"msg": message})
        else:
            messages.error(request, _("Connection test: FAILED — %(msg)s") % {"msg": message})
        return redirect("dashboard-payment-method-configure", pk=config.pk)

    if config.method != PaymentMethod.SSLCOMMERZ:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {"ok": False, "status": "FAILED", "message": "Not implemented."},
                status=400,
            )
        messages.error(request, _("Test connection is only available for SSLCommerz and bKash sandbox."))
        return redirect("dashboard-payment-methods")

    status, message = test_sslcommerz_connection(actor=request.user)
    # Strip secrets from any accidental leakage.
    safe = {
        "ok": status == "SUCCESS",
        "status": status,
        "message": message,
    }
    if "passwd" in message.lower() or "password" in message.lower() and "credential" not in message.lower():
        safe["message"] = "Gateway response recorded (details redacted)."

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(safe)

    if status == "SUCCESS":
        messages.success(request, _("Connection test: SUCCESS — %(msg)s") % {"msg": safe["message"]})
    elif status == "NOT_CONFIGURED":
        messages.warning(request, _("Connection test: NOT CONFIGURED — %(msg)s") % {"msg": safe["message"]})
    else:
        messages.error(request, _("Connection test: FAILED — %(msg)s") % {"msg": safe["message"]})
    return redirect("dashboard-payment-method-configure", pk=config.pk)


# =========================================================================
# Donations list / detail / manual entry
# =========================================================================

@login_required
def donations_list(request):
    if not _require(request, "donations", "view"):
        return redirect("dashboard")

    qs = Donation.objects.select_related("category", "transaction", "user").order_by("-created_at")
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()
    dtype = request.GET.get("type", "").strip()

    if q:
        qs = qs.filter(
            Q(donor_name__icontains=q)
            | Q(donor_phone__icontains=q)
            | Q(donor_email__icontains=q)
            | Q(receipt_number__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category_id=category)
    if dtype == "online":
        qs = qs.filter(payment_method="SSLCOMMERZ")
    elif dtype == "manual":
        qs = qs.exclude(payment_method="SSLCOMMERZ")
    elif dtype == "anonymous":
        qs = qs.filter(is_anonymous=True)

    totals = qs.filter(status=DonationStatus.COMPLETED).aggregate(total=Sum("amount"), count=Count("id"))

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/donations/list.html",
        {
            "page_obj": page_obj,
            "donations": page_obj.object_list,
            "q": q,
            "status": status,
            "category": category,
            "dtype": dtype,
            "status_choices": DonationStatus.choices,
            "categories": DonationCategory.objects.all().order_by("name_en"),
            "totals": totals,
            "can_create": _require(request, "donations", "create"),
            "can_export": _require(request, "donations", "export"),
        },
    )


@login_required
def donation_detail(request, pk):
    if not _require(request, "donations", "view"):
        return redirect("dashboard")
    donation = get_object_or_404(
        Donation.objects.select_related("category", "transaction", "user"), pk=pk
    )
    return render(request, "dashboard/donations/detail.html", {"donation": donation})


@login_required
def donation_manual_create(request):
    if not _require(request, "donations", "create"):
        return redirect("dashboard-donations")
    if request.method == "POST":
        form = ManualDonationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            donation = create_manual_donation(
                amount=cd["amount"],
                category=cd["category"],
                donor_name=cd.get("donor_name", ""),
                donor_phone=cd.get("donor_phone", ""),
                donor_email=cd.get("donor_email", ""),
                payment_method=cd["payment_method"],
                is_anonymous=cd.get("is_anonymous", False),
                message=cd.get("message", ""),
                recorded_by=request.user,
            )
            messages.success(request, _("Manual donation recorded (%(rn)s).") % {"rn": donation.receipt_number or donation.pk})
            return redirect("dashboard-donation-detail", pk=donation.pk)
    else:
        form = ManualDonationForm()

    from django.urls import reverse

    return render(
        request,
        "dashboard/generic/form.html",
        {"form": form, "page_title": _("Record Manual Donation"), "cancel_url": reverse("dashboard-donations")},
    )


# =========================================================================
# Reports
# =========================================================================

@login_required
def donation_reports(request):
    if not _require(request, "donations", "export") and not _require(request, "donations", "view"):
        return redirect("dashboard")

    completed = Donation.objects.filter(status=DonationStatus.COMPLETED)

    by_category = (
        completed.values("category__name_en")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    by_month = (
        completed.annotate(period=TruncMonth("created_at"))
        .values("period")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-period")[:12]
    )
    by_year = (
        completed.annotate(period=TruncYear("created_at"))
        .values("period")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-period")
    )
    by_day = (
        completed.annotate(period=TruncDay("created_at"))
        .values("period")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-period")[:30]
    )
    anonymous = completed.filter(is_anonymous=True).aggregate(total=Sum("amount"), count=Count("id"))
    grand = completed.aggregate(total=Sum("amount"), count=Count("id"))

    return render(
        request,
        "dashboard/donations/reports.html",
        {
            "by_category": by_category,
            "by_month": by_month,
            "by_year": by_year,
            "by_day": by_day,
            "anonymous": anonymous,
            "grand": grand,
        },
    )
