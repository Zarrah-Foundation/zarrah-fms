from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView as AuthLoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.forms import (
    ForgotPasswordForm,
    LoginForm,
    RegisterForm,
    ResendVerificationForm,
    ResetPasswordForm,
)
from accounts.models import User
from accounts.verification import (
    can_resend_verification,
    issue_email_verify_token,
    mark_resend_attempt,
    send_verification_email,
)
from core.email import send_email
from core.models import SiteSettings


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("verify-pending")

    def form_valid(self, form):
        user = form.save()
        verify_url = self.request.build_absolute_uri(f"/verify/{user.email_verify_token}/")
        send_verification_email(user, verify_url)
        self.request.session["pending_verify_email"] = user.email
        return super().form_valid(form)


class LoginView(AuthLoginView):
    template_name = "accounts/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("dashboard")


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect("home")

    def get(self, request):
        return redirect("home")


class VerifyPendingView(TemplateView):
    template_name = "accounts/verify_pending.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pending_email"] = self.request.session.get("pending_verify_email", "")
        ctx["form"] = ResendVerificationForm(initial={"email": ctx["pending_email"]})
        return ctx


class ResendVerificationView(View):
    """Resend verification email with rate limiting. Avoids account enumeration."""

    def post(self, request):
        form = ResendVerificationForm(request.POST)
        if not form.is_valid():
            messages.error(request, _("Please provide a valid email address."))
            return redirect("verify-pending")

        email = (
            form.cleaned_data.get("email")
            or request.session.get("pending_verify_email")
            or ""
        ).strip()
        if not email:
            messages.error(request, _("Please provide a valid email address."))
            return redirect("verify-pending")

        allowed, wait, reason = can_resend_verification(email)
        # Always show the same success-style message when rate-limited or not,
        # except for explicit cooldown feedback.
        if not allowed and reason == "cooldown":
            messages.info(
                request,
                _("Please wait %(seconds)s seconds before requesting another link.")
                % {"seconds": wait},
            )
            return redirect("verify-pending")
        if not allowed and reason == "hourly_limit":
            messages.info(
                request,
                _("Too many verification requests. Please try again later."),
            )
            return redirect("verify-pending")

        mark_resend_attempt(email)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            messages.info(
                request,
                _("If an account exists and still needs verification, a new link has been sent."),
            )
            return redirect("verify-pending")

        if user.email_verified:
            messages.info(request, _("This email is already verified. You can log in."))
            return redirect("login")

        issue_email_verify_token(user)
        verify_url = request.build_absolute_uri(f"/verify/{user.email_verify_token}/")
        send_verification_email(user, verify_url)
        request.session["pending_verify_email"] = user.email
        messages.info(
            request,
            _("If an account exists and still needs verification, a new link has been sent."),
        )
        return redirect("verify-pending")


class VerifyEmailView(View):
    def get(self, request, token):
        try:
            user = User.objects.get(email_verify_token=token)
        except User.DoesNotExist:
            messages.error(request, _("Invalid or expired verification link."))
            return redirect("verify-pending")
        if user.email_verify_token_expiry and user.email_verify_token_expiry < timezone.now():
            messages.error(request, _("Verification link has expired. Please request a new one."))
            return redirect("verify-pending")
        user.email_verified = timezone.now()
        user.email_verify_token = None
        user.email_verify_token_expiry = None
        user.save(
            update_fields=[
                "email_verified",
                "email_verify_token",
                "email_verify_token_expiry",
                "updated_at",
            ]
        )
        messages.success(request, _("Email verified successfully. You can now log in."))
        return redirect("login")


class ForgotPasswordView(FormView):
    template_name = "accounts/forgot_password.html"
    form_class = ForgotPasswordForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            messages.info(self.request, _("If an account exists, a reset link has been sent."))
            return super().form_valid(form)
        import secrets
        from datetime import timedelta

        from django.conf import settings

        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expiry = timezone.now() + timedelta(
            seconds=getattr(settings, "PASSWORD_RESET_TIMEOUT", 86400)
        )
        user.save(update_fields=["reset_token", "reset_token_expiry", "updated_at"])
        reset_url = self.request.build_absolute_uri(f"/reset-password/{user.reset_token}/")
        foundation = SiteSettings.load().localized_name()
        send_email(
            subject=_("Password Reset - %(name)s") % {"name": foundation},
            message=_("Reset your password: %(url)s") % {"url": reset_url},
            recipient_list=[email],
            fail_silently=True,
        )
        messages.info(self.request, _("If an account exists, a reset link has been sent."))
        return super().form_valid(form)


class ResetPasswordView(FormView):
    template_name = "accounts/reset_password.html"
    form_class = ResetPasswordForm
    success_url = reverse_lazy("login")

    def dispatch(self, request, token, *args, **kwargs):
        try:
            self.user = User.objects.get(reset_token=token)
        except User.DoesNotExist:
            messages.error(request, _("Invalid reset link."))
            return redirect("login")
        if self.user.reset_token_expiry and self.user.reset_token_expiry < timezone.now():
            messages.error(request, _("Reset link has expired."))
            return redirect("login")
        return super().dispatch(request, token, *args, **kwargs)

    def form_valid(self, form):
        self.user.set_password(form.cleaned_data["password1"])
        self.user.reset_token = None
        self.user.reset_token_expiry = None
        self.user.save(update_fields=["password", "reset_token", "reset_token_expiry", "updated_at"])
        messages.success(self.request, _("Password reset successfully."))
        return super().form_valid(form)
