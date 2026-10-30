"""Dashboard-managed Site Settings, SMTP and SMS Settings (no Django admin needed)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.email import send_test_email
from core.models import SiteSettings, SmsSettings, SmtpSettings
from dashboard.forms import SiteSettingsForm, SmsSettingsForm, SmtpSettingsForm
from rbac.permissions import has_action


def _deny_unless(request, module, action):
    return not has_action(request.user, module, action)


@login_required
def site_settings_edit(request):
    if _deny_unless(request, "site_settings", "view"):
        return redirect("dashboard")
    obj = SiteSettings.load()
    can_edit = has_action(request.user, "site_settings", "edit")

    if request.method == "POST":
        if not can_edit:
            messages.error(request, _("You don't have permission to edit site settings."))
            return redirect("dashboard-site-settings")
        form = SiteSettingsForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("Site settings saved."))
            return redirect("dashboard-site-settings")
    else:
        form = SiteSettingsForm(instance=obj)

    return render(
        request,
        "dashboard/settings/site.html",
        {"form": form, "obj": obj, "can_edit": can_edit},
    )


@login_required
def smtp_settings_edit(request):
    if _deny_unless(request, "site_settings", "view"):
        return redirect("dashboard")
    obj = SmtpSettings.load()
    can_edit = has_action(request.user, "site_settings", "edit")

    if request.method == "POST":
        if not can_edit:
            messages.error(request, _("You don't have permission to edit SMTP settings."))
            return redirect("dashboard-smtp-settings")
        form = SmtpSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("SMTP settings saved."))
            return redirect("dashboard-smtp-settings")
    else:
        form = SmtpSettingsForm(instance=obj)

    return render(
        request,
        "dashboard/settings/smtp.html",
        {"form": form, "obj": obj, "can_edit": can_edit, "default_to": request.user.email},
    )


@login_required
@require_POST
def smtp_send_test(request):
    if _deny_unless(request, "site_settings", "edit"):
        return redirect("dashboard-smtp-settings")
    to_email = (request.POST.get("to_email") or "").strip()
    if not to_email:
        messages.error(request, _("Please enter a recipient email address."))
    else:
        try:
            send_test_email(to_email)
            messages.success(request, _("Test email sent to %(email)s.") % {"email": to_email})
        except Exception as exc:  # noqa: BLE001
            messages.error(request, _("Failed to send test email: %(error)s") % {"error": exc})
    return redirect("dashboard-smtp-settings")


@login_required
def sms_settings_edit(request):
    if _deny_unless(request, "site_settings", "view"):
        return redirect("dashboard")
    obj = SmsSettings.load()
    can_edit = has_action(request.user, "site_settings", "edit")

    if request.method == "POST":
        if not can_edit:
            messages.error(request, _("You don't have permission to edit SMS settings."))
            return redirect("dashboard-sms-settings")
        form = SmsSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, _("SMS settings saved."))
            return redirect("dashboard-sms-settings")
    else:
        form = SmsSettingsForm(instance=obj)

    return render(
        request,
        "dashboard/settings/sms.html",
        {"form": form, "obj": obj, "can_edit": can_edit},
    )
