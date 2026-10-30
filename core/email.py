"""Email helpers: prefer active SMTP Settings, fall back to Django/.env settings."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection

from core.models import SmtpSettings


def smtp_timeout_seconds() -> int:
    """Bounded SMTP socket timeout (seconds). Never unbounded."""
    try:
        value = int(getattr(settings, "EMAIL_TIMEOUT", 20) or 20)
    except (TypeError, ValueError):
        value = 20
    return max(5, min(value, 120))


def get_smtp_config():
    """Return SmtpSettings if active and usable, else None (use .env)."""
    smtp = SmtpSettings.load()
    if smtp.is_active and smtp.host and smtp.from_email:
        return smtp
    return None


def get_mail_connection(*, fail_silently: bool = False):
    """Return an SMTP connection with an explicit socket timeout."""
    timeout = smtp_timeout_seconds()
    smtp = get_smtp_config()
    if smtp is None:
        return get_connection(
            fail_silently=fail_silently,
            timeout=timeout,
        )
    use_ssl = bool(smtp.use_ssl)
    use_tls = bool(smtp.use_tls) and not use_ssl
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=smtp.host,
        port=smtp.port,
        username=smtp.username or None,
        password=smtp.password or None,
        use_tls=use_tls,
        use_ssl=use_ssl,
        fail_silently=fail_silently,
        timeout=timeout,
    )


def get_from_email():
    smtp = get_smtp_config()
    if smtp is not None:
        name = (smtp.from_name or "").strip()
        if name:
            return f"{name} <{smtp.from_email}>"
        return smtp.from_email
    return getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")


def get_reply_to():
    smtp = get_smtp_config()
    if smtp is not None and smtp.reply_to:
        return [smtp.reply_to]
    return None


def public_smtp_diagnostics() -> dict:
    """Safe diagnostic snapshot — never includes passwords/secrets."""
    smtp = get_smtp_config()
    if smtp is not None:
        return {
            "source": "database",
            "host": smtp.host or "",
            "port": smtp.port,
            "use_tls": bool(smtp.use_tls) and not bool(smtp.use_ssl),
            "use_ssl": bool(smtp.use_ssl),
            "encryption": smtp.encryption,
            "username_set": bool((smtp.username or "").strip()),
            "password_set": bool((smtp.password or "").strip()),
            "from_email_set": bool((smtp.from_email or "").strip()),
            "timeout_seconds": smtp_timeout_seconds(),
            "is_active": True,
        }
    return {
        "source": "environment",
        "host": getattr(settings, "EMAIL_HOST", "") or "",
        "port": int(getattr(settings, "EMAIL_PORT", 587) or 587),
        "use_tls": bool(getattr(settings, "EMAIL_USE_TLS", False)),
        "use_ssl": bool(getattr(settings, "EMAIL_USE_SSL", False)),
        "encryption": "SSL"
        if getattr(settings, "EMAIL_USE_SSL", False)
        else ("TLS" if getattr(settings, "EMAIL_USE_TLS", False) else "NONE"),
        "username_set": bool(getattr(settings, "EMAIL_HOST_USER", "") or ""),
        "password_set": bool(getattr(settings, "EMAIL_HOST_PASSWORD", "") or ""),
        "from_email_set": bool(getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""),
        "timeout_seconds": smtp_timeout_seconds(),
        "is_active": True,
    }


def send_email(
    *,
    subject: str,
    message: str,
    recipient_list: list[str],
    html_message: str | None = None,
    fail_silently: bool = False,
    attachments: list | None = None,
) -> int:
    """Send email using DB SMTP when active, otherwise Django settings (.env)."""
    recipients = [r for r in recipient_list if r]
    if not recipients:
        return 0

    if html_message:
        email = EmailMultiAlternatives(
            subject=subject,
            body=message or "",
            from_email=get_from_email(),
            to=recipients,
            reply_to=get_reply_to(),
            connection=get_mail_connection(fail_silently=fail_silently),
        )
        email.attach_alternative(html_message, "text/html")
    else:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=get_from_email(),
            to=recipients,
            reply_to=get_reply_to(),
            connection=get_mail_connection(fail_silently=fail_silently),
        )
    if attachments:
        for att in attachments:
            if len(att) == 2:
                email.attach(att[0], att[1])
            else:
                email.attach(att[0], att[1], att[2])
    return email.send(fail_silently=fail_silently)


def send_test_email(to_email: str) -> None:
    send_email(
        subject="Zarrah Foundation — SMTP test",
        message=(
            "This is a test email from Zarrah Foundation.\n\n"
            "If you received this, your SMTP configuration is working."
        ),
        recipient_list=[to_email],
        fail_silently=False,
    )
