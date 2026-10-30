import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import FormView, TemplateView

from core.education_data import (
    EDUCATION_CLASSES,
    EDUCATION_STAGES,
    EDUCATION_TYPES,
)
from core.templatetags.i18n_extras import zf_text
from members.forms import (
    ApplicationStatusLookupForm,
    MemberApplicationForm,
    MissingDocumentUploadForm,
)
from members.models import ApplicationDocumentRequest, ApplicationEvent, MemberApplication
from members.services import (
    can_request_status_lookup,
    consume_status_token,
    find_application_for_status_lookup,
    issue_status_token,
    mark_status_lookup_attempt,
    send_status_lookup_email,
    upload_requested_document,
)
from members.transitions import record_event

STATUS_SESSION_KEY = "application_status_id"


class MembershipInfoView(TemplateView):
    template_name = "members/membership.html"

    def get_context_data(self, **kwargs):
        from members.models import MembershipFeeSettings
        from pages.organization_data import MEMBERSHIP_ELIGIBILITY, MEMBERSHIP_FEES

        ctx = super().get_context_data(**kwargs)
        ctx["membership_eligibility"] = MEMBERSHIP_ELIGIBILITY
        ctx["constitutional_fees"] = MEMBERSHIP_FEES
        ctx["fee_settings"] = MembershipFeeSettings.load()
        return ctx


class MemberApplicationView(FormView):
    template_name = "members/apply.html"
    form_class = MemberApplicationForm
    success_url = "/membership/"

    def is_ajax(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # The Bangladesh geo dataset (divisions/districts/upazilas) is fetched
        # lazily client-side from static/data/bd/*.json instead of being
        # embedded here — see static/js/bd-address.js.
        ctx["education_data_json"] = json.dumps(
            {
                "types": EDUCATION_TYPES,
                "stages": EDUCATION_STAGES,
                "classes": EDUCATION_CLASSES,
            }
        )
        return ctx

    def form_valid(self, form):
        application = form.save()
        record_event(
            application,
            ApplicationEvent.Action.CREATED,
            message="Public membership application submitted",
            metadata={"reference_code": application.reference_code},
        )
        messages.success(
            self.request,
            zf_text(
                "Your application has been submitted. Reference: %(ref)s. We will review it shortly. Use Check Application Status with this reference and your email to track progress."
            )
            % {"ref": application.reference_code},
        )
        if self.is_ajax():
            return JsonResponse({"success": True, "redirect": self.get_success_url()})
        return super().form_valid(form)

    def form_invalid(self, form):
        # Returned for both normal and AJAX submissions. The AJAX branch lets
        # the front-end apply errors in place (see membership-form.js) instead
        # of reloading the page — which would otherwise clear any selected
        # file inputs, a browser security restriction we cannot bypass.
        if self.is_ajax():
            errors = {name: [str(e) for e in errs] for name, errs in form.errors.items()}
            non_field_errors = [str(e) for e in form.non_field_errors()]
            return JsonResponse(
                {"success": False, "errors": errors, "non_field_errors": non_field_errors},
                status=400,
            )
        return super().form_invalid(form)


@require_http_methods(["GET", "POST"])
def application_status_request(request):
    """Reference + email → one-time link. Anti-enumeration response always."""
    form = ApplicationStatusLookupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        allowed, wait, reason = can_request_status_lookup(email)
        if not allowed:
            if reason == "cooldown":
                messages.error(
                    request,
                    _("Please wait %(seconds)s seconds before trying again.")
                    % {"seconds": wait},
                )
            else:
                messages.error(
                    request,
                    _("Too many status requests. Please try again later."),
                )
        else:
            mark_status_lookup_attempt(email)
            application = find_application_for_status_lookup(
                form.cleaned_data["reference_code"], email
            )
            if application:
                token = issue_status_token(application)
                absolute = request.build_absolute_uri(
                    reverse("membership-status-token", kwargs={"token": token})
                )
                send_status_lookup_email(application, absolute)
            messages.success(
                request,
                zf_text(
                    "If an application matches that reference and email, a one-time status link has been sent. Please check your inbox."
                ),
            )
            return redirect("membership-status")
    return render(
        request,
        "members/status_request.html",
        {"form": form},
    )


@require_http_methods(["GET"])
def application_status_token(request, token):
    application = consume_status_token(token)
    if not application:
        messages.error(request, _("This status link is invalid or has expired."))
        return redirect("membership-status")
    request.session[STATUS_SESSION_KEY] = str(application.pk)
    return redirect("membership-status-view")


def _application_from_status_session(request):
    app_id = request.session.get(STATUS_SESSION_KEY)
    if not app_id:
        return None
    return MemberApplication.objects.filter(pk=app_id).first()


@require_http_methods(["GET"])
def application_status_view(request):
    application = _application_from_status_session(request)
    if not application:
        messages.error(request, _("Please request a new status link to continue."))
        return redirect("membership-status")
    open_requests = list(application.open_document_requests())
    return render(
        request,
        "members/status_view.html",
        {
            "application": application,
            "open_requests": open_requests,
            "upload_form": MissingDocumentUploadForm(),
        },
    )


@require_POST
def application_status_upload(request, request_id):
    application = _application_from_status_session(request)
    if not application:
        messages.error(request, _("Please request a new status link to continue."))
        return redirect("membership-status")
    doc_request = get_object_or_404(
        ApplicationDocumentRequest,
        pk=request_id,
        application=application,
        is_satisfied=False,
    )
    form = MissingDocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            upload_requested_document(doc_request, form.cleaned_data["uploaded_file"])
            messages.success(request, _("Document uploaded successfully."))
        except Exception as exc:
            messages.error(request, str(exc) or _("Could not upload document."))
    else:
        messages.error(request, _("Could not upload document. Check the file type and size."))
    return redirect("membership-status-view")
