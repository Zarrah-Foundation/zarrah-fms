"""
SSLCommerz payment-gateway adapter (documented one-time hosted checkout only).
"""

import logging

import requests
from django.urls import reverse

from core.choices import PaymentMethod
from donations.gateways.base import PaymentGateway, PaymentGatewayError
from donations.money import amounts_equal, normalize_currency

logger = logging.getLogger(__name__)


def _payable_customer(payable):
    txn = payable.transaction
    name = (
        getattr(payable, "donor_name", None)
        or getattr(payable, "cus_name", None)
        or getattr(txn, "cus_name", None)
        or "Customer"
    )
    email = (
        getattr(payable, "donor_email", None)
        or getattr(txn, "cus_email", None)
        or ""
    )
    phone = (
        getattr(payable, "donor_phone", None)
        or getattr(txn, "cus_phone", None)
        or ""
    )
    return name, email, phone


def _product_name(payable):
    if hasattr(payable, "product_name"):
        return payable.product_name
    category = getattr(payable, "category", None)
    if category is not None:
        return getattr(category, "name_en", None) or "Donation"
    return "Payment"


def _callback_urls(payable, request):
    purpose = getattr(payable, "payment_purpose", None) or getattr(
        getattr(payable, "transaction", None), "purpose", None
    )
    if purpose in ("MEMBERSHIP_FEE", "MEMBERSHIP_REG", "MEMBERSHIP_REGISTRATION"):
        return {
            "success_url": request.build_absolute_uri(reverse("membership-fee-pay-success")),
            "fail_url": request.build_absolute_uri(reverse("membership-fee-pay-fail")),
            "cancel_url": request.build_absolute_uri(reverse("membership-fee-pay-cancel")),
            "ipn_url": request.build_absolute_uri(reverse("membership-fee-pay-ipn")),
        }
    if purpose == "DONATION_RECURRING" or getattr(payable, "is_recurring_authorization", False):
        return {
            "success_url": request.build_absolute_uri(reverse("donation-recurring-success")),
            "fail_url": request.build_absolute_uri(reverse("donation-recurring-fail")),
            "cancel_url": request.build_absolute_uri(reverse("donation-recurring-cancel")),
            "ipn_url": request.build_absolute_uri(reverse("donation-recurring-ipn")),
        }
    return {
        "success_url": request.build_absolute_uri("/donation/success/"),
        "fail_url": request.build_absolute_uri("/donation/fail/"),
        "cancel_url": request.build_absolute_uri("/donation/cancel/"),
        "ipn_url": request.build_absolute_uri("/donation/ipn/"),
    }


class SSLCommerzGateway(PaymentGateway):
    code = PaymentMethod.SSLCOMMERZ
    supports_one_time = True
    supports_recurring = True  # code support — availability gated by config
    supports_refund = True  # code surface — merchant must enable + verify
    supports_cancel_recurring = False
    supports_webhook = True
    supports_validate = True

    def refund(self, *, transaction, amount, reason=""):
        """SSLCommerz refund API is not auto-called without merchant verification.

        Never invent a successful refund response.
        """
        from donations.models import PaymentMethodConfig

        cfg = PaymentMethodConfig.objects.filter(method=PaymentMethod.SSLCOMMERZ).first()
        if cfg is None or not cfg.refunds_enabled:
            raise PaymentGatewayError("Provider refund: Not configured.")
        if not cfg.refund_verified_at:
            raise PaymentGatewayError(
                "SSLCommerz refund API is enabled in admin but not live-verified. "
                "No refund was sent to the gateway."
            )
        raise PaymentGatewayError(
            "SSLCommerz refund execution requires a verified merchant refund integration."
        )

    def init_payment(self, payable, request):
        """Create a one-time hosted checkout session. No recurring/schedule params."""
        from donations.credential_service import gateway_urls, resolve_sslcommerz_credentials

        transaction = payable.transaction
        cus_name, cus_email, cus_phone = _payable_customer(payable)
        urls = _callback_urls(payable, request)
        product = _product_name(payable)
        purpose = getattr(payable, "payment_purpose", "") or ""
        category = "Membership" if purpose.startswith("MEMBERSHIP") else "Donation"

        creds = resolve_sslcommerz_credentials()
        if not creds.configured:
            raise PaymentGatewayError("SSLCommerz credentials are not configured.")
        gateway_url, _validation_url = gateway_urls(creds.is_sandbox)

        payload = {
            "store_id": creds.store_id,
            "store_passwd": creds.store_password,
            "total_amount": str(payable.amount),
            "currency": getattr(payable, "currency", None) or transaction.currency or "BDT",
            "tran_id": transaction.tran_id,
            "success_url": urls["success_url"],
            "fail_url": urls["fail_url"],
            "cancel_url": urls["cancel_url"],
            "ipn_url": urls["ipn_url"],
            "cus_name": cus_name,
            "cus_email": cus_email or "",
            "cus_phone": cus_phone or "",
            "cus_add1": "Bangladesh",
            "cus_city": "Dhaka",
            "cus_country": "Bangladesh",
            "ship_name": cus_name,
            "ship_add1": "Bangladesh",
            "ship_city": "Dhaka",
            "ship_country": "Bangladesh",
            "shipping_method": "NO",
            "product_name": product,
            "product_category": category,
            "product_profile": "non-physical-goods",
        }

        logger.info(
            "SSLCommerz init tran_id=%s amount=%s sandbox=%s source=%s",
            transaction.tran_id,
            payable.amount,
            creds.is_sandbox,
            creds.source,
        )

        try:
            response = requests.post(
                gateway_url,
                data=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.exception("SSLCommerz Request Error")
            raise PaymentGatewayError(f"Connection error: {e}")
        except ValueError:
            logger.exception("SSLCommerz Invalid JSON")
            raise PaymentGatewayError(f"Invalid JSON response:\n{response.text}")

        if data.get("status") != "SUCCESS":
            logger.error(
                "SSLCommerz Init Failed status=%s reason=%s",
                data.get("status"),
                data.get("failedreason") or data.get("failed_reason"),
            )
            raise PaymentGatewayError(
                data.get("failedreason")
                or data.get("failed_reason")
                or str(data.get("status") or "FAILED")
            )

        page_url = data.get("GatewayPageURL")
        if not page_url:
            raise PaymentGatewayError(
                "GatewayPageURL was not returned by SSLCommerz."
            )
        return page_url

    def init_recurring_authorization(self, payable, request, *, subscription, schedule_day):
        """Hosted checkout with encrypted EasyCheckout ``schedule`` (gateway-scheduled).

        Requires configured SALT + plan refer. Does not invent merchant-initiated charges.
        """
        from donations.credential_service import gateway_urls, resolve_sslcommerz_credentials
        from donations.recurring_config import sslcommerz_recurring_configured
        from donations.recurring_crypto import encrypt_schedule_payload

        status = sslcommerz_recurring_configured()
        if not status.configured:
            raise PaymentGatewayError(status.reason)

        # Mark payable so callback URLs resolve to recurring endpoints.
        payable.is_recurring_authorization = True
        payable.payment_purpose = "DONATION_RECURRING"

        transaction = payable.transaction
        cus_name, cus_email, cus_phone = _payable_customer(payable)
        urls = _callback_urls(payable, request)
        creds = resolve_sslcommerz_credentials()
        if not creds.configured:
            raise PaymentGatewayError("SSLCommerz credentials are not configured.")
        gateway_url, _validation_url = gateway_urls(creds.is_sandbox)

        day = int(schedule_day)
        if day < 1 or day > 28:
            day = min(28, max(1, day))

        schedule = {
            "refer": status.plan_refer,
            "acct_no": str(subscription.pk),
            "type": "monthly",
            "dayofmonth": str(day),
        }
        encrypted = encrypt_schedule_payload(schedule, salt_key=__import__(
            "donations.recurring_config", fromlist=["sslcommerz_recurring_salt"]
        ).sslcommerz_recurring_salt())

        payload = {
            "store_id": creds.store_id,
            "store_passwd": creds.store_password,
            "total_amount": str(payable.amount),
            "currency": getattr(payable, "currency", None) or transaction.currency or "BDT",
            "tran_id": transaction.tran_id,
            "success_url": urls["success_url"],
            "fail_url": urls["fail_url"],
            "cancel_url": urls["cancel_url"],
            "ipn_url": urls["ipn_url"],
            "cus_name": cus_name,
            "cus_email": cus_email or "",
            "cus_phone": cus_phone or "",
            "cus_add1": "Bangladesh",
            "cus_city": "Dhaka",
            "cus_country": "Bangladesh",
            "ship_name": cus_name,
            "ship_add1": "Bangladesh",
            "ship_city": "Dhaka",
            "ship_country": "Bangladesh",
            "shipping_method": "NO",
            "product_name": "Recurring donation",
            "product_category": "Donation",
            "product_profile": "non-physical-goods",
            "schedule": encrypted,
            # Custom fields for IPN correlation (never secrets).
            "value_a": str(subscription.pk),
            "value_b": "RECURRING_DONATION",
            "value_c": "AUTHORIZATION",
        }

        logger.info(
            "SSLCommerz recurring init tran_id=%s subscription=%s sandbox=%s",
            transaction.tran_id,
            subscription.pk,
            creds.is_sandbox,
        )

        try:
            response = requests.post(gateway_url, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.exception("SSLCommerz recurring Request Error")
            raise PaymentGatewayError(f"Connection error: {e}")
        except ValueError:
            logger.exception("SSLCommerz recurring Invalid JSON")
            raise PaymentGatewayError(f"Invalid JSON response:\n{response.text}")

        if data.get("status") != "SUCCESS":
            raise PaymentGatewayError(
                data.get("failedreason")
                or data.get("failed_reason")
                or str(data.get("status") or "FAILED")
            )
        page_url = data.get("GatewayPageURL")
        if not page_url:
            raise PaymentGatewayError("GatewayPageURL was not returned by SSLCommerz.")
        return page_url

    def validate_transaction(self, val_id, tran_id, amount, currency="BDT"):
        from donations.credential_service import gateway_urls, resolve_sslcommerz_credentials

        creds = resolve_sslcommerz_credentials()
        if not creds.configured:
            return None
        _gateway_url, validation_url = gateway_urls(creds.is_sandbox)
        params = {
            "val_id": val_id,
            "store_id": creds.store_id,
            "store_passwd": creds.store_password,
            "format": "json",
        }

        response = requests.get(
            validation_url,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        logger.info(
            "Validation Response status=%s tran_id=%s",
            data.get("status"),
            data.get("tran_id"),
        )

        if data.get("status") not in ("VALID", "VALIDATED"):
            return None
        if data.get("tran_id") != tran_id:
            return None
        if not amounts_equal(data.get("amount"), amount):
            logger.warning(
                "SSLCommerz amount mismatch tran_id=%s expected=%s got=%s",
                tran_id,
                amount,
                data.get("amount"),
            )
            return None
        expected_currency = normalize_currency(currency)
        remote_currency = data.get("currency")
        if remote_currency and normalize_currency(remote_currency) != expected_currency:
            logger.warning(
                "SSLCommerz currency mismatch tran_id=%s expected=%s got=%s",
                tran_id,
                expected_currency,
                remote_currency,
            )
            return None
        # Do NOT require store_amount == charged amount. store_amount is the
        # merchant net (after gateway fees / sandbox sample discounts).
        return data
