"""Public + guest recurring donation views (PAY-WP3)."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView

from core.choices import DonationStatus, PaymentMethod
from donations.models import (
    DonationRecurringCharge,
    DonationSubscription,
    RecurringChargeKind,
    SubscriptionStatus,
)
from donations.recurring_config import sslcommerz_recurring_configured
from donations.recurring_forms import RecurringDonationForm
from donations.recurring_services import (
    RecurringDonationError,
    cancel_subscription,
    complete_authorization_from_gateway,
    create_recurring_subscription,
    get_subscription_by_management_token,
    record_webhook_event,
    settle_recurring_ipn,
    start_recurring_authorization,
)
from donations.services import validate_transaction

logger = logging.getLogger(__name__)

MANAGE_RATE_LIMIT = 30
MANAGE_RATE_WINDOW = 3600


def _client_ip(request):
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or request.META.get("REMOTE_ADDR") or "unknown"


def _manage_rate_ok(request) -> bool:
    key = f"recurring_manage:{_client_ip(request)}"
    count = cache.get(key) or 0
    if count >= MANAGE_RATE_LIMIT:
        return False
    cache.set(key, count + 1, MANAGE_RATE_WINDOW)
    return True


class RecurringDonationCreateView(FormView):
    template_name = "donations/recurring.html"
    form_class = RecurringDonationForm

    def dispatch(self, request, *args, **kwargs):
        from core.templatetags.i18n_extras import zf_text
        from donations.gateway_capabilities import cms_new_recurring_enabled

        if not cms_new_recurring_enabled():
            messages.info(
                request, zf_text("New recurring donations are currently unavailable.")
            )
            return redirect("donation")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from core.templatetags.i18n_extras import zf_text
        from donations.gateway_capabilities import recurring_checkout_allowed

        ctx = super().get_context_data(**kwargs)
        status = sslcommerz_recurring_configured()
        ok, err = recurring_checkout_allowed()
        ctx["recurring_configured"] = status.configured
        ctx["recurring_signup_allowed"] = ok
        if ok:
            ctx["recurring_config_reason"] = ""
        else:
            ctx["recurring_config_reason"] = zf_text(
                "Recurring donations are not available right now."
            )
        ctx["recurring_frequency_label"] = zf_text("Monthly")
        ctx["recurring_provider_label"] = "SSLCommerz"
        return ctx

    def form_valid(self, form):
        from core.templatetags.i18n_extras import zf_text
        from donations.gateway_capabilities import (
            CMS_RECURRING_DISABLED_MSG,
            recurring_checkout_allowed,
        )

        ok, err = recurring_checkout_allowed()
        if not ok:
            if err == CMS_RECURRING_DISABLED_MSG:
                messages.info(
                    self.request,
                    zf_text("New recurring donations cannot be started."),
                )
                return redirect("donation")
            messages.error(
                self.request,
                zf_text("Recurring donations are not available right now."),
            )
            return redirect("donation-recurring")

        kwargs = form.build_subscription_kwargs()
        user = self.request.user if self.request.user.is_authenticated else None
        try:
            sub = create_recurring_subscription(user=user, **kwargs)
            _sub, _charge, url = start_recurring_authorization(sub, request=self.request)
        except RecurringDonationError as exc:
            if getattr(exc, "code", "") == "cms_disabled":
                messages.info(
                    self.request, zf_text("New recurring donations cannot be started.")
                )
                return redirect("donation")
            messages.error(self.request, str(exc))
            return redirect("donation-recurring")
        except Exception:
            logger.exception("Recurring authorization init failed")
            messages.error(self.request, zf_text("Payment initialization failed."))
            return redirect("donation-recurring")
        return redirect(url)

    def form_invalid(self, form):
        from core.templatetags.i18n_extras import zf_text

        messages.error(self.request, zf_text("Please correct the errors below."))
        return self.render_to_response(self.get_context_data(form=form))


def _gateway_params(request):
    return request.POST if request.method == "POST" else request.GET


def _authorize_from_validated(request, *, require_browser_message=True):
    """Validate with SSLCommerz then activate. Browser alone never activates."""
    params = _gateway_params(request)
    val_id = params.get("val_id")
    tran_id = params.get("tran_id")
    if not val_id or not tran_id:
        if require_browser_message:
            messages.error(request, _("Invalid payment response."))
        return None, "invalid"

    charge = (
        DonationRecurringCharge.objects.select_related("subscription", "transaction")
        .filter(
            transaction__tran_id=tran_id,
            kind=RecurringChargeKind.AUTHORIZATION,
        )
        .first()
    )
    if charge is None:
        if require_browser_message:
            messages.error(request, _("Subscription authorization not found."))
        return None, "not_found"

    data = validate_transaction(
        val_id,
        tran_id,
        charge.amount,
        method=PaymentMethod.SSLCOMMERZ,
        currency=charge.currency or "BDT",
    )
    if not data:
        if require_browser_message:
            messages.error(request, _("Payment validation failed."))
        return None, "validation"

    event, _created = record_webhook_event(
        PaymentMethod.SSLCOMMERZ, {**params, **data}, event_type="auth_return"
    )
    try:
        charge = complete_authorization_from_gateway(
            tran_id=tran_id,
            val_id=val_id,
            validation_data=data,
            event=event,
        )
    except RecurringDonationError as exc:
        if require_browser_message:
            messages.error(request, str(exc))
        return None, "error"
    return charge, "ok"


@method_decorator(csrf_exempt, name="dispatch")
class RecurringSuccessView(View):
    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        charge, status = _authorize_from_validated(request)
        if status != "ok" or charge is None:
            return redirect("donation-recurring")
        sub = charge.subscription
        request.session["recurring_manage_token"] = sub.management_token or ""
        messages.success(request, _("Your monthly donation is now active. Thank you!"))
        return render(
            request,
            "donations/recurring_success.html",
            {
                "subscription": sub,
                "charge": charge,
                "management_token": sub.management_token,
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class RecurringFailView(View):
    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        from donations.webhook_services import (
            mark_webhook_ignored,
            mark_webhook_processed,
            record_webhook_event,
        )

        params = _gateway_params(request)
        payload = params.dict() if hasattr(params, "dict") else dict(params)
        event, _created = record_webhook_event(
            PaymentMethod.SSLCOMMERZ, payload, event_type="recurring_fail_return"
        )
        tran_id = params.get("tran_id")
        if tran_id:
            charge = DonationRecurringCharge.objects.filter(
                transaction__tran_id=tran_id,
                kind=RecurringChargeKind.AUTHORIZATION,
            ).select_related("subscription", "transaction").first()
            if charge and charge.subscription.status == SubscriptionStatus.ACTIVE:
                mark_webhook_ignored(event, "Subscription already active")
            elif charge and charge.subscription.status != SubscriptionStatus.ACTIVE:
                charge.subscription.status = SubscriptionStatus.DRAFT
                charge.subscription.save(update_fields=["status", "updated_at"])
                if charge.transaction_id:
                    charge.transaction.status = DonationStatus.FAILED
                    charge.transaction.save(update_fields=["status"])
                mark_webhook_processed(event)
            else:
                mark_webhook_ignored(event, "Authorization charge not found")
        else:
            mark_webhook_ignored(event, "Missing tran_id")
        messages.error(request, _("Recurring donation authorization failed."))
        return render(request, "donations/recurring_fail.html")


@method_decorator(csrf_exempt, name="dispatch")
class RecurringCancelReturnView(View):
    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        from donations.webhook_services import (
            mark_webhook_ignored,
            mark_webhook_processed,
            record_webhook_event,
        )

        params = _gateway_params(request)
        payload = params.dict() if hasattr(params, "dict") else dict(params)
        event, _created = record_webhook_event(
            PaymentMethod.SSLCOMMERZ, payload, event_type="recurring_cancel_return"
        )
        tran_id = params.get("tran_id")
        if tran_id:
            charge = DonationRecurringCharge.objects.filter(
                transaction__tran_id=tran_id,
                kind=RecurringChargeKind.AUTHORIZATION,
            ).select_related("subscription", "transaction").first()
            if charge and charge.subscription.status == SubscriptionStatus.ACTIVE:
                mark_webhook_ignored(event, "Subscription already active")
            elif charge and charge.subscription.status != SubscriptionStatus.ACTIVE:
                charge.subscription.status = SubscriptionStatus.DRAFT
                charge.subscription.save(update_fields=["status", "updated_at"])
                if charge.transaction_id:
                    charge.transaction.status = DonationStatus.CANCELLED
                    charge.transaction.save(update_fields=["status"])
                mark_webhook_processed(event)
            else:
                mark_webhook_ignored(event, "Authorization charge not found")
        else:
            mark_webhook_ignored(event, "Missing tran_id")
        messages.warning(request, _("Recurring donation authorization was cancelled."))
        return render(request, "donations/recurring_cancel.html")


@csrf_exempt
@require_POST
def recurring_ipn(request):
    """IPN for authorization and gateway-scheduled recurring settlements."""
    payload = request.POST.dict()
    val_id = payload.get("val_id")
    tran_id = payload.get("tran_id")
    if not val_id and not tran_id and not payload.get("subscription_id"):
        return HttpResponse("Invalid", status=400)

    event, created = record_webhook_event(
        PaymentMethod.SSLCOMMERZ, payload, event_type="ipn"
    )
    if not created and event.processing_status == "PROCESSED":
        return HttpResponse("Already processed")

    # Authorization path: known setup tran_id
    auth_charge = None
    if tran_id:
        auth_charge = DonationRecurringCharge.objects.filter(
            transaction__tran_id=tran_id,
            kind=RecurringChargeKind.AUTHORIZATION,
        ).select_related("subscription").first()

    if auth_charge is not None:
        if not val_id or not tran_id:
            return HttpResponse("Invalid", status=400)
        data = validate_transaction(
            val_id,
            tran_id,
            auth_charge.amount,
            method=PaymentMethod.SSLCOMMERZ,
            currency=auth_charge.currency or "BDT",
        )
        if not data:
            return HttpResponse("Validation failed", status=400)
        try:
            complete_authorization_from_gateway(
                tran_id=tran_id,
                val_id=val_id,
                validation_data=data,
                event=event,
            )
        except RecurringDonationError:
            logger.exception("Recurring auth IPN failed")
            return HttpResponse("Error", status=400)
        return HttpResponse("OK")

    # Gateway-scheduled recurring settlement
    amount = auth_charge.amount if auth_charge else payload.get("amount")
    expected_amount = amount
    if payload.get("value_a"):
        sub = DonationSubscription.objects.filter(pk=payload.get("value_a")).first()
        if sub:
            expected_amount = sub.amount
    if not val_id or not tran_id:
        return HttpResponse("Invalid", status=400)
    data = validate_transaction(
        val_id,
        tran_id,
        expected_amount or payload.get("amount") or 0,
        method=PaymentMethod.SSLCOMMERZ,
        currency="BDT",
    )
    if not data:
        return HttpResponse("Validation failed", status=400)
    # Merge safe gateway fields for settlement matching
    merged = {**payload, **data}
    try:
        charge = settle_recurring_ipn(validation_data=merged, event=event)
    except RecurringDonationError:
        logger.exception("Recurring settle IPN failed")
        return HttpResponse("Error", status=400)
    if charge is None:
        return HttpResponse("Rejected", status=400)
    return HttpResponse("OK")


class GuestRecurringManageView(View):
    """Token-based guest management — never UUID-only public access."""

    def get(self, request, token):
        if not _manage_rate_ok(request):
            return HttpResponseForbidden("Too many requests")
        sub = get_subscription_by_management_token(token)
        if sub is None:
            messages.error(request, _("This management link is invalid or expired."))
            return redirect("donation-recurring")
        charges = sub.charges.order_by("-created_at")[:20]
        return render(
            request,
            "donations/recurring_manage.html",
            {"subscription": sub, "charges": charges, "token": token},
        )

    def post(self, request, token):
        if not _manage_rate_ok(request):
            return HttpResponseForbidden("Too many requests")
        sub = get_subscription_by_management_token(token)
        if sub is None:
            messages.error(request, _("This management link is invalid or expired."))
            return redirect("donation-recurring")
        action = request.POST.get("action")
        if action == "cancel":
            cancel_subscription(
                sub,
                actor=request.user if request.user.is_authenticated else None,
                reason="Cancelled via guest management link",
            )
            messages.success(request, _("Your recurring donation has been cancelled."))
            return redirect("donation-recurring-manage", token=token)
        return redirect("donation-recurring-manage", token=token)
