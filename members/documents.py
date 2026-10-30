"""Member and application PDF generation (Bengali-capable ReportLab)."""

from __future__ import annotations

import io
from typing import Any, Iterable

from django.utils import timezone
from django.utils.translation import get_language, gettext as _

from core.models import SiteSettings
from members.models import Member, MemberApplication
from members.positions import effective_assignments, format_position_label, primary_assignment


def _foundation_names() -> tuple[str, str]:
    site = SiteSettings.load()
    bn = (getattr(site, "foundation_name_bn", "") or "").strip()
    en = (getattr(site, "foundation_name_en", "") or "").strip()
    return bn or "জাররাহ ফাউন্ডেশন", en or "Zarrah Foundation"


def build_member_context(member: Member, *, include_history: bool = False) -> dict[str, Any]:
    """Presentation context for a member profile PDF (no private file contents)."""
    lang = (get_language() or "en").split("-")[0].lower()
    user = getattr(member, "user", None)
    mtype = getattr(member, "membership_type", None)
    primary = primary_assignment(member)
    active = list(effective_assignments(member))
    history = []
    if include_history:
        history = list(
            member.position_assignments.select_related("position").order_by(
                "-start_date", "position__display_order"
            )
        )

    positions_active = [
        {
            "label": format_position_label(a, lang=lang),
            "start_date": a.start_date,
            "end_date": a.end_date,
            "is_primary": a.is_primary,
            "notes": a.notes or "",
        }
        for a in active
    ]
    positions_history = [
        {
            "label": format_position_label(a, lang=lang),
            "start_date": a.start_date,
            "end_date": a.end_date,
            "is_primary": a.is_primary,
            "is_active": a.is_active,
            "notes": a.notes or "",
        }
        for a in history
    ]

    return {
        "foundation_name_bn": _foundation_names()[0],
        "foundation_name_en": _foundation_names()[1],
        "member_id": member.member_id,
        "first_name": member.first_name or "",
        "last_name": member.last_name or "",
        "full_name": f"{member.first_name} {member.last_name}".strip() or member.member_id,
        "phone": member.phone or "",
        "email": getattr(user, "email", "") or "",
        "gender": member.get_gender_display() if member.gender else "",
        "date_of_birth": member.date_of_birth,
        "blood_group": member.blood_group or "",
        "nid_number": member.nid_number or "",
        "status": member.get_status_display() if member.status else "",
        "membership_type": (
            (mtype.name_bn if lang == "bn" else mtype.name_en) if mtype else ""
        ),
        "membership_type_en": getattr(mtype, "name_en", "") or "",
        "membership_type_bn": getattr(mtype, "name_bn", "") or "",
        "joined_at": member.joined_at,
        "present_address": member.present_address or "",
        "permanent_address": member.permanent_address or "",
        "district": member.district or "",
        "upazila": member.upazila or "",
        "occupation": member.occupation or "",
        "organization": member.organization or "",
        "education": member.education or "",
        "emergency_name": member.emergency_name or "",
        "emergency_phone": member.emergency_phone or "",
        "emergency_relation": member.emergency_relation or "",
        "is_founder": bool(member.is_founder),
        "primary_position": format_position_label(primary, lang=lang),
        "positions_active": positions_active,
        "positions_history": positions_history if include_history else [],
        "include_history": include_history,
        "generated_at": timezone.localtime(),
    }


def build_application_context(application: MemberApplication) -> dict[str, Any]:
    """Presentation context for an application PDF (no private file contents)."""
    return {
        "foundation_name_bn": _foundation_names()[0],
        "foundation_name_en": _foundation_names()[1],
        "reference_code": application.reference_code or str(application.pk)[:8],
        "bangla_name": application.bangla_name or "",
        "english_name": application.english_name or "",
        "full_name": application.full_name
        or application.english_name
        or application.bangla_name
        or "",
        "father_name": application.father_name or "",
        "mother_name": application.mother_name or "",
        "email": application.email or "",
        "phone": application.phone or "",
        "gender": application.get_gender_display() if application.gender else "",
        "date_of_birth": application.date_of_birth,
        "identity_type": (
            application.get_identity_type_display() if application.identity_type else ""
        ),
        "identity_number": application.identity_number or "",
        "present_district": application.present_district or "",
        "present_upazila": application.present_upazila or "",
        "present_address": application.present_address or "",
        "occupation": application.occupation or "",
        "organization": application.organization or "",
        "education": application.education or "",
        "status": application.get_status_display() if application.status else "",
        "created_at": application.created_at,
        "reviewed_at": application.reviewed_at,
        "generated_at": timezone.localtime(),
    }


def _fmt_date(value) -> str:
    if not value:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y")
    return str(value)


def _fmt_dt(value) -> str:
    if not value:
        return "—"
    if hasattr(value, "strftime"):
        return timezone.localtime(value).strftime("%d %b %Y %H:%M")
    return str(value)


def _kv_table(rows: list[tuple[str, str]], styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    from core.pdf_fonts import escape_pdf_text

    data = [
        [
            Paragraph(escape_pdf_text(k), styles["label"]),
            Paragraph(escape_pdf_text(v), styles["body"]),
        ]
        for k, v in rows
        if v not in (None, "")
    ]
    if not data:
        return None
    table = Table(data, colWidths=[45 * mm, 125 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#E5E7EB")),
            ]
        )
    )
    return table


def _member_story(ctx: dict[str, Any], styles) -> list:
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer

    from core.pdf_fonts import escape_pdf_text

    story = [
        Paragraph(
            escape_pdf_text(ctx["foundation_name_bn"], bold=True), styles["title"]
        ),
        Paragraph(escape_pdf_text(ctx["foundation_name_en"]), styles["small"]),
        Spacer(1, 3 * mm),
        Paragraph(escape_pdf_text(_("Member Profile"), bold=True), styles["heading"]),
        Paragraph(
            escape_pdf_text(
                _("Generated %(when)s") % {"when": _fmt_dt(ctx["generated_at"])}
            ),
            styles["small"],
        ),
        Spacer(1, 4 * mm),
    ]

    meta = [
        (_("Member ID"), ctx["member_id"]),
        (_("Name"), ctx["full_name"]),
        (_("Status"), ctx["status"]),
        (_("Membership type"), ctx["membership_type"]),
        (_("Primary position"), ctx["primary_position"]),
        (_("Phone"), ctx["phone"]),
        (_("Email"), ctx["email"]),
        (_("Gender"), ctx["gender"]),
        (_("Date of birth"), _fmt_date(ctx["date_of_birth"])),
        (_("Blood group"), ctx["blood_group"]),
        (_("NID"), ctx["nid_number"]),
        (_("Joined"), _fmt_date(ctx["joined_at"])),
        (_("District"), ctx["district"]),
        (_("Upazila"), ctx["upazila"]),
        (_("Present address"), ctx["present_address"]),
        (_("Permanent address"), ctx["permanent_address"]),
        (_("Occupation"), ctx["occupation"]),
        (_("Organization"), ctx["organization"]),
        (_("Education"), ctx["education"]),
        (
            _("Emergency contact"),
            " / ".join(
                p
                for p in (
                    ctx["emergency_name"],
                    ctx["emergency_phone"],
                    ctx["emergency_relation"],
                )
                if p
            ),
        ),
    ]
    if ctx["is_founder"]:
        meta.append((_("Founder"), _("Yes")))
    table = _kv_table(meta, styles)
    if table:
        story.append(table)

    if ctx["positions_active"]:
        story.append(Spacer(1, 4 * mm))
        story.append(
            Paragraph(
                escape_pdf_text(_("Organizational positions"), bold=True),
                styles["heading"],
            )
        )
        for pos in ctx["positions_active"]:
            line = pos["label"]
            if pos["is_primary"]:
                line += f" ({_('Primary')})"
            dates = f"{_fmt_date(pos['start_date'])} – {_fmt_date(pos['end_date'])}"
            story.append(Paragraph(escape_pdf_text(f"• {line} — {dates}"), styles["body"]))

    if ctx.get("include_history") and ctx.get("positions_history"):
        story.append(Spacer(1, 3 * mm))
        story.append(
            Paragraph(
                escape_pdf_text(_("Position history"), bold=True),
                styles["heading"],
            )
        )
        for pos in ctx["positions_history"]:
            status = _("Active") if pos["is_active"] else _("Ended")
            dates = f"{_fmt_date(pos['start_date'])} – {_fmt_date(pos['end_date'])}"
            story.append(
                Paragraph(
                    escape_pdf_text(f"• {pos['label']} ({status}) — {dates}"),
                    styles["body"],
                )
            )

    return story


def _application_story(ctx: dict[str, Any], styles) -> list:
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer

    from core.pdf_fonts import escape_pdf_text

    story = [
        Paragraph(
            escape_pdf_text(ctx["foundation_name_bn"], bold=True), styles["title"]
        ),
        Paragraph(escape_pdf_text(ctx["foundation_name_en"]), styles["small"]),
        Spacer(1, 3 * mm),
        Paragraph(
            escape_pdf_text(_("Membership Application"), bold=True), styles["heading"]
        ),
        Paragraph(
            escape_pdf_text(
                _("Generated %(when)s") % {"when": _fmt_dt(ctx["generated_at"])}
            ),
            styles["small"],
        ),
        Spacer(1, 4 * mm),
    ]
    meta = [
        (_("Reference"), ctx["reference_code"]),
        (_("English name"), ctx["english_name"]),
        (_("Bangla name"), ctx["bangla_name"]),
        (_("Father"), ctx["father_name"]),
        (_("Mother"), ctx["mother_name"]),
        (_("Status"), ctx["status"]),
        (_("Phone"), ctx["phone"]),
        (_("Email"), ctx["email"]),
        (_("Gender"), ctx["gender"]),
        (_("Date of birth"), _fmt_date(ctx["date_of_birth"])),
        (_("Identity"), f"{ctx['identity_type']} — {ctx['identity_number']}".strip(" —")),
        (_("District"), ctx["present_district"]),
        (_("Upazila"), ctx["present_upazila"]),
        (_("Present address"), ctx["present_address"]),
        (_("Occupation"), ctx["occupation"]),
        (_("Organization"), ctx["organization"]),
        (_("Education"), ctx["education"]),
        (_("Submitted"), _fmt_dt(ctx["created_at"])),
        (_("Reviewed"), _fmt_dt(ctx["reviewed_at"])),
    ]
    table = _kv_table(meta, styles)
    if table:
        story.append(table)
    return story


def generate_member_pdf(
    member: Member, *, actor=None, include_history: bool = False
) -> bytes:
    """Return PDF bytes for a single member profile."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    from core.pdf_fonts import ensure_pdf_fonts, pdf_paragraph_styles

    ensure_pdf_fonts()
    styles = pdf_paragraph_styles()
    ctx = build_member_context(member, include_history=include_history)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Member {ctx['member_id']}",
        author="Zarrah Foundation",
    )
    doc.build(_member_story(ctx, styles))
    return buffer.getvalue()


def generate_application_pdf(application: MemberApplication, *, actor=None) -> bytes:
    """Return PDF bytes for a single membership application."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate

    from core.pdf_fonts import ensure_pdf_fonts, pdf_paragraph_styles

    ensure_pdf_fonts()
    styles = pdf_paragraph_styles()
    ctx = build_application_context(application)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Application {ctx['reference_code']}",
        author="Zarrah Foundation",
    )
    doc.build(_application_story(ctx, styles))
    return buffer.getvalue()


def generate_bulk_members_pdf(
    members: Iterable[Member], *, actor=None, include_history: bool = False
) -> bytes:
    """Cover page + one page-break per member."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    from core.pdf_fonts import ensure_pdf_fonts, escape_pdf_text, pdf_paragraph_styles

    ensure_pdf_fonts()
    styles = pdf_paragraph_styles()
    members_list = list(members)
    bn, en = _foundation_names()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_("Members report"),
        author="Zarrah Foundation",
    )
    story = [
        Paragraph(escape_pdf_text(bn, bold=True), styles["title"]),
        Paragraph(escape_pdf_text(en), styles["small"]),
        Spacer(1, 8 * mm),
        Paragraph(escape_pdf_text(_("Members report"), bold=True), styles["heading"]),
        Paragraph(
            escape_pdf_text(
                _("%(count)d member(s)") % {"count": len(members_list)}
            ),
            styles["body"],
        ),
        Paragraph(
            escape_pdf_text(
                _("Generated %(when)s")
                % {"when": timezone.localtime().strftime("%d %b %Y %H:%M")}
            ),
            styles["small"],
        ),
    ]
    for member in members_list:
        story.append(PageBreak())
        ctx = build_member_context(member, include_history=include_history)
        story.extend(_member_story(ctx, styles))
    doc.build(story)
    return buffer.getvalue()


def generate_bulk_applications_pdf(
    applications: Iterable[MemberApplication], *, actor=None
) -> bytes:
    """Cover page + one page-break per application."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    from core.pdf_fonts import ensure_pdf_fonts, escape_pdf_text, pdf_paragraph_styles

    ensure_pdf_fonts()
    styles = pdf_paragraph_styles()
    apps_list = list(applications)
    bn, en = _foundation_names()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=_("Applications report"),
        author="Zarrah Foundation",
    )
    story = [
        Paragraph(escape_pdf_text(bn, bold=True), styles["title"]),
        Paragraph(escape_pdf_text(en), styles["small"]),
        Spacer(1, 8 * mm),
        Paragraph(
            escape_pdf_text(_("Applications report"), bold=True), styles["heading"]
        ),
        Paragraph(
            escape_pdf_text(
                _("%(count)d application(s)") % {"count": len(apps_list)}
            ),
            styles["body"],
        ),
        Paragraph(
            escape_pdf_text(
                _("Generated %(when)s")
                % {"when": timezone.localtime().strftime("%d %b %Y %H:%M")}
            ),
            styles["small"],
        ),
    ]
    for application in apps_list:
        story.append(PageBreak())
        ctx = build_application_context(application)
        story.extend(_application_story(ctx, styles))
    doc.build(story)
    return buffer.getvalue()
