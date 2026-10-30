"""Public resolution share views (token-based, no login required)."""

from __future__ import annotations

from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.signals import get_client_ip
from dashboard.forms_governance import PublicSharePasswordForm
from governance.documents import resolution_file_response
from governance.services.public_share import (
    get_valid_share,
    password_attempts_blocked,
    verify_share_password,
)

_SESSION_KEY = "gov_public_share_ok"


def _session_unlocked(request, token: str) -> bool:
    unlocked = request.session.get(_SESSION_KEY) or []
    return token in unlocked


def _mark_unlocked(request, token: str) -> None:
    unlocked = list(request.session.get(_SESSION_KEY) or [])
    if token not in unlocked:
        unlocked.append(token)
        request.session[_SESSION_KEY] = unlocked
        request.session.modified = True


def _share_or_404(token: str):
    share = get_valid_share(token)
    if share is None:
        raise Http404("Shared resolution not found.")
    return share


def _password_gate(request, share):
    """Return redirect to password page if needed, else None."""
    if not share.requires_password:
        return None
    if _session_unlocked(request, share.token):
        return None
    return redirect("public-resolution-password", token=share.token)


def _public_context(share):
    resolution = share.resolution
    version = resolution.current_version
    meeting = resolution.meeting
    signers = []
    if share.show_signer_details and version is not None:
        for sig in version.signatures.select_related("member").all():
            signers.append(
                {
                    "name": sig.signer_name,
                    "designation": sig.signer_designation,
                    "signed_at": sig.signed_at,
                }
            )
    return {
        "share": share,
        "resolution": resolution,
        "version": version,
        "meeting": meeting,
        "meeting_ref": meeting.reference_id,
        "meeting_title": meeting.localized_title("en") or meeting.title_bn,
        "signers": signers,
    }


@require_http_methods(["GET"])
def public_resolution_view(request, token: str):
    share = _share_or_404(token)
    gate = _password_gate(request, share)
    if gate is not None:
        return gate
    return render(request, "governance/public/share.html", _public_context(share))


@require_http_methods(["GET", "POST"])
def public_resolution_password(request, token: str):
    share = _share_or_404(token)
    if not share.requires_password:
        return redirect("public-resolution", token=token)
    if _session_unlocked(request, token):
        return redirect("public-resolution", token=token)

    ip = get_client_ip(request) or ""
    blocked = password_attempts_blocked(ip, token)
    form = PublicSharePasswordForm(request.POST or None)

    if request.method == "POST" and not blocked and form.is_valid():
        if verify_share_password(share, form.cleaned_data["password"], ip=ip):
            _mark_unlocked(request, token)
            return redirect("public-resolution", token=token)
        form.add_error("password", "Incorrect password.")
        blocked = password_attempts_blocked(ip, token)

    return render(
        request,
        "governance/public/password.html",
        {"form": form, "blocked": blocked, "share": share},
    )


@require_http_methods(["GET"])
def public_resolution_pdf(request, token: str):
    share = _share_or_404(token)
    gate = _password_gate(request, share)
    if gate is not None:
        return gate
    return resolution_file_response(share.resolution, fmt="pdf")


@require_http_methods(["GET"])
def public_resolution_docx(request, token: str):
    share = _share_or_404(token)
    gate = _password_gate(request, share)
    if gate is not None:
        return gate
    return resolution_file_response(share.resolution, fmt="docx")
