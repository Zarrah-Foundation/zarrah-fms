import json
import uuid

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView
from django.db.models import Prefetch

from core.choices import DonationStatus, PaymentMethod
from donations.forms import DonationForm
from donations.models import Donation, DonationCategory, DonationQuickAmount, Transaction
from donations.receipts import generate_receipt_pdf, receipt_context, receipt_filename
from donations.ownership import user_can_access_donation
from donations.services import (
    complete_donation,
    generate_tran_id,
    init_payment,
    mark_donation_failed,
    send_receipt_email,
    validate_transaction,
)


def _active_categories():
    return (
        DonationCategory.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch(
                "quick_amounts",
                queryset=DonationQuickAmount.objects.filter(is_active=True).order_by(
                    "display_order", "amount"
                ),
            )
        )
        .order_by("display_order", "name_en")
    )


def _quick_amounts_payload(categories, lang):
    payload = {}
    for category in categories:
        payload[str(category.pk)] = [
            {"amount": qa.amount, "label": qa.label(lang)}
            for qa in category.quick_amounts.all()
        ]
    return payload


def _donation_page_extras():
    from donations.gateway_capabilities import online_checkout_allowed, public_recurring_option_visible
    from donations.models import TransactionPurpose

    bkash_ok, _bkash_err = online_checkout_allowed(
        PaymentMethod.BKASH, TransactionPurpose.DONATION
    )
    return {
        "show_recurring_option": public_recurring_option_visible(),
        "bkash_checkout_available": bkash_ok,
    }


class DonationListView(ListView):
    model = DonationCategory
    template_name = "donations/donation.html"
    context_object_name = "categories"

    def get_queryset(self):
        return _active_categories()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        categories = list(ctx["categories"])
        lang = "bn" if get_language() == "bn" else "en"
        form = DonationForm()
        ctx["donation_form"] = form
        ctx["default_category"] = (
            next((c for c in categories if c.is_default), None)
            or (categories[0] if categories else None)
        )
        ctx["quick_amounts_json"] = json.dumps(
            _quick_amounts_payload(categories, lang), ensure_ascii=False
        )
        ctx.update(_donation_page_extras())
        return ctx


class DonationCreateView(FormView):
    template_name = "donations/donation.html"
    form_class = DonationForm
    success_url = "/donation/"

    def get_initial(self):
        initial = super().get_initial()
        category_id = self.request.GET.get("category")
        if category_id:
            initial["category"] = category_id
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        categories = list(_active_categories())
        lang = "bn" if get_language() == "bn" else "en"
        ctx["categories"] = categories
        ctx["donation_form"] = ctx.get("form") or self.get_form()
        ctx["default_category"] = (
            next((c for c in categories if c.is_default), None)
            or (categories[0] if categories else None)
        )
        ctx["quick_amounts_json"] = json.dumps(
            _quick_amounts_payload(categories, lang), ensure_ascii=False
        )
        ctx.update(_donation_page_extras())
        return ctx

    def form_valid(self, form):
        from donations.gateway_capabilities import online_checkout_allowed
        from donations.models import TransactionPurpose

        method = (self.request.POST.get("payment_method") or PaymentMethod.SSLCOMMERZ).strip()
        if method not in (PaymentMethod.SSLCOMMERZ, PaymentMethod.BKASH):
            method = PaymentMethod.SSLCOMMERZ
        ok, err = online_checkout_allowed(method, purpose=TransactionPurpose.DONATION)
        if not ok:
            messages.error(self.request, err)
            return redirect("donation")

        kwargs = form.build_donation_kwargs()
        if self.request.user.is_authenticated:
            kwargs["user"] = self.request.user
        kwargs["payment_method"] = method

        tran_id = generate_tran_id()
        session_id = str(uuid.uuid4())
        transaction = Transaction.objects.create(
            session_id=session_id,
            tran_id=tran_id,
            amount=kwargs["amount"],
            cus_name=kwargs["donor_name"],
            cus_email=kwargs.get("donor_email"),
            cus_phone=kwargs.get("donor_phone"),
            gateway=method,
        )
        donation = Donation.objects.create(transaction=transaction, **kwargs)
        try:
            gateway_url = init_payment(donation, self.request, method=method)
            return redirect(gateway_url)
        except Exception as e:
            from donations.gateways.bkash import safe_gateway_message

            transaction.status = DonationStatus.FAILED
            transaction.error = safe_gateway_message(e) if method == PaymentMethod.BKASH else str(e)[:300]
            transaction.save()
            donation.status = DonationStatus.FAILED
            donation.save(update_fields=["status", "updated_at"])
            from core.templatetags.i18n_extras import zf_text

            messages.error(self.request, zf_text("Payment initialization failed."))
            return redirect("donation")

    def form_invalid(self, form):
        from core.templatetags.i18n_extras import zf_text

        messages.error(self.request, zf_text("Please correct the errors below."))
        return self.render_to_response(self.get_context_data(form=form))


def _gateway_params(request):
    """SSLCommerz may return via GET or POST to success/fail/cancel URLs."""
    return request.POST if request.method == "POST" else request.GET


@method_decorator(csrf_exempt, name="dispatch")
class DonationSuccessView(View):
    """Browser return URL — CSRF-exempt; completion still requires server-side validation."""

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        from donations.webhook_services import (
            mark_webhook_failed,
            mark_webhook_processed,
            record_webhook_event,
            webhook_already_processed,
        )

        params = _gateway_params(request)
        payload = params.dict() if hasattr(params, "dict") else dict(params)
        event, _created = record_webhook_event(
            PaymentMethod.SSLCOMMERZ, payload, event_type="donation_success_return"
        )
        val_id = params.get("val_id")
        tran_id = params.get("tran_id")
        if not val_id or not tran_id:
            mark_webhook_failed(event, "Missing val_id or tran_id")
            messages.error(request, _("Invalid payment response."))
            return redirect("donation")
        try:
            donation = Donation.objects.select_related("transaction", "category").get(
                transaction__tran_id=tran_id
            )
        except Donation.DoesNotExist:
            mark_webhook_failed(event, "Donation not found")
            messages.error(request, _("Donation not found."))
            return redirect("donation")
        if donation.status == DonationStatus.COMPLETED:
            mark_webhook_processed(event)
            request.session["donation_receipt_access"] = str(donation.pk)
            messages.success(request, _("Thank you for your donation!"))
            return render(request, "donations/success.html", {"donation": donation})
        if webhook_already_processed(event):
            # Duplicate return after IPN completed the payment.
            donation.refresh_from_db()
            if donation.status == DonationStatus.COMPLETED:
                request.session["donation_receipt_access"] = str(donation.pk)
                messages.success(request, _("Thank you for your donation!"))
                return render(request, "donations/success.html", {"donation": donation})
        data = validate_transaction(
            val_id,
            tran_id,
            donation.amount,
            method=donation.payment_method,
            currency=donation.currency,
        )
        if not data:
            mark_webhook_failed(event, "Gateway validation failed")
            messages.error(request, _("Payment validation failed."))
            return redirect("donation")
        complete_donation(donation, val_id=val_id, validation_data=data)
        donation.refresh_from_db()
        mark_webhook_processed(event)
        request.session["donation_receipt_access"] = str(donation.pk)
        messages.success(request, _("Thank you for your donation!"))
        return render(request, "donations/success.html", {"donation": donation})


@method_decorator(csrf_exempt, name="dispatch")
class DonationFailView(View):
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
            PaymentMethod.SSLCOMMERZ, payload, event_type="donation_fail_return"
        )
        tran_id = params.get("tran_id")
        if tran_id:
            try:
                donation = Donation.objects.select_related("transaction").get(
                    transaction__tran_id=tran_id
                )
                if donation.status == DonationStatus.COMPLETED:
                    mark_webhook_ignored(event, "Donation already completed")
                else:
                    mark_donation_failed(donation, notify=True)
                    mark_webhook_processed(event)
            except Donation.DoesNotExist:
                Transaction.objects.filter(tran_id=tran_id).update(
                    status=DonationStatus.FAILED
                )
                mark_webhook_processed(event)
        else:
            mark_webhook_ignored(event, "Missing tran_id")
        messages.error(request, _("Payment failed."))
        return render(request, "donations/fail.html")


@method_decorator(csrf_exempt, name="dispatch")
class DonationCancelView(View):
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
            PaymentMethod.SSLCOMMERZ, payload, event_type="donation_cancel_return"
        )
        tran_id = params.get("tran_id")
        if tran_id:
            updated = Donation.objects.filter(transaction__tran_id=tran_id).exclude(
                status=DonationStatus.COMPLETED
            ).update(status=DonationStatus.CANCELLED)
            Transaction.objects.filter(tran_id=tran_id).exclude(
                status=DonationStatus.COMPLETED
            ).update(status=DonationStatus.CANCELLED)
            if updated:
                mark_webhook_processed(event)
            else:
                mark_webhook_ignored(event, "Already completed or not found")
        else:
            mark_webhook_ignored(event, "Missing tran_id")
        messages.warning(request, _("Payment cancelled."))
        return render(request, "donations/cancel.html")


@csrf_exempt
@require_POST
def donation_ipn(request):
    from donations.webhook_services import (
        mark_webhook_failed,
        mark_webhook_processed,
        record_webhook_event,
        webhook_already_processed,
    )

    payload = request.POST.dict()
    event, _created = record_webhook_event(
        PaymentMethod.SSLCOMMERZ, payload, event_type="donation_ipn"
    )
    if webhook_already_processed(event):
        return HttpResponse("Already processed")

    val_id = payload.get("val_id")
    tran_id = payload.get("tran_id")
    if not val_id or not tran_id:
        mark_webhook_failed(event, "Missing val_id or tran_id")
        return HttpResponse("Invalid", status=400)
    try:
        donation = Donation.objects.select_related("transaction").get(
            transaction__tran_id=tran_id
        )
    except Donation.DoesNotExist:
        mark_webhook_failed(event, "Donation not found")
        return HttpResponse("Not found", status=404)
    if donation.status == DonationStatus.COMPLETED:
        mark_webhook_processed(event)
        return HttpResponse("Already processed")
    data = validate_transaction(
        val_id,
        tran_id,
        donation.amount,
        method=donation.payment_method,
        currency=donation.currency,
    )
    if not data:
        mark_webhook_failed(event, "Gateway validation failed")
        return HttpResponse("Validation failed", status=400)
    complete_donation(donation, val_id=val_id, validation_data=data)
    mark_webhook_processed(event)
    return HttpResponse("OK")


def _get_completed_donation(pk):
    return get_object_or_404(
        Donation.objects.select_related("transaction", "category"),
        pk=pk,
        status=DonationStatus.COMPLETED,
    )


def _receipt_access_allowed(request, donation) -> bool:
    if user_can_access_donation(request.user, donation):
        return True
    session_key = request.session.get("donation_receipt_access")
    return bool(session_key and str(donation.pk) == str(session_key))


class DonationReceiptView(View):
    """Printable HTML receipt."""

    def get(self, request, pk):
        donation = _get_completed_donation(pk)
        if not _receipt_access_allowed(request, donation):
            messages.error(request, _("You do not have permission to view this receipt."))
            return redirect("login" if not request.user.is_authenticated else "dashboard-my-donations")
        return render(
            request,
            "donations/receipt.html",
            receipt_context(donation),
        )


class DonationReceiptPdfView(View):
    def get(self, request, pk):
        donation = _get_completed_donation(pk)
        if not _receipt_access_allowed(request, donation):
            messages.error(request, _("You do not have permission to download this receipt."))
            return redirect("login" if not request.user.is_authenticated else "dashboard-my-donations")
        pdf = generate_receipt_pdf(donation)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{receipt_filename(donation)}"'
        return response


class DonationReceiptEmailView(View):
    """Re-send receipt email for a completed donation."""

    def post(self, request, pk):
        donation = _get_completed_donation(pk)
        if not _receipt_access_allowed(request, donation):
            messages.error(request, _("You do not have permission to email this receipt."))
            return redirect("login" if not request.user.is_authenticated else "dashboard-my-donations")
        if not donation.donor_email:
            messages.error(request, _("No email address is on file for this donation."))
        else:
            ok = send_receipt_email(donation, force=True)
            if ok:
                messages.success(request, _("Receipt emailed successfully."))
            else:
                messages.error(request, _("Could not send the receipt email."))
        return redirect("donation-receipt", pk=donation.pk)
