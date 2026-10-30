"""Safe SMTP connectivity diagnostic — never prints credentials."""

from __future__ import annotations

import socket

from django.core.management.base import BaseCommand, CommandError

from core.email import public_smtp_diagnostics, send_test_email, smtp_timeout_seconds


class Command(BaseCommand):
    help = (
        "Diagnose SMTP configuration and optionally send a test message. "
        "Never prints passwords or secrets."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            dest="to_email",
            default="",
            help="Recipient for a real test send (required unless --probe-only).",
        )
        parser.add_argument(
            "--probe-only",
            action="store_true",
            help="Only check DNS/TCP and print safe diagnostics (no email sent).",
        )

    def handle(self, *args, **options):
        diag = public_smtp_diagnostics()
        timeout = smtp_timeout_seconds()
        self.stdout.write("SMTP diagnostics (secrets redacted):")
        for key in (
            "source",
            "host",
            "port",
            "use_tls",
            "use_ssl",
            "encryption",
            "username_set",
            "password_set",
            "from_email_set",
            "timeout_seconds",
        ):
            self.stdout.write(f"  {key}: {diag.get(key)}")

        host = diag.get("host") or ""
        port = int(diag.get("port") or 0)
        if not host or not port:
            raise CommandError("SMTP host/port not configured.")

        if diag.get("use_tls") and diag.get("use_ssl"):
            raise CommandError(
                "Invalid SMTP mode: both TLS and SSL are enabled. "
                "Use SSL for port 465, or TLS (STARTTLS) for port 587."
            )
        if port == 465 and diag.get("use_tls") and not diag.get("use_ssl"):
            self.stderr.write(
                self.style.WARNING(
                    "Port 465 with STARTTLS (TLS) often hangs. Prefer SMTP_USE_SSL=True."
                )
            )

        self.stdout.write(f"Probing TCP {host}:{port} (timeout={timeout}s)…")
        try:
            socket.setdefaulttimeout(min(timeout, 15))
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            addr = infos[0][4] if infos else None
            self.stdout.write(f"  DNS: OK ({addr})")
            with socket.create_connection((host, port), timeout=min(timeout, 15)):
                self.stdout.write("  TCP: OK")
        except OSError as exc:
            raise CommandError(f"SMTP network probe failed: {type(exc).__name__}") from exc

        if options["probe_only"]:
            self.stdout.write(self.style.SUCCESS("Probe-only complete (no email sent)."))
            return

        to_email = (options.get("to_email") or "").strip()
        if not to_email:
            raise CommandError("Provide --to=email@example.com or use --probe-only.")

        self.stdout.write(f"Sending test email to {to_email} (timeout={timeout}s)…")
        try:
            send_test_email(to_email)
        except Exception as exc:
            raise CommandError(
                f"SMTP send failed within {timeout}s: {type(exc).__name__}: {exc}"
            ) from exc
        self.stdout.write(self.style.SUCCESS("SMTP test send succeeded."))
