"""Donation receipt rendering (HTML context + PDF bytes)."""

from __future__ import annotations

import io
from pathlib import Path

from django.utils import timezone
from django.utils.translation import get_language, gettext as _

from core.models import SiteSettings


def receipt_context(donation):
    site = SiteSettings.load()
    lang = (get_language() or "en").split("-")[0].lower()
    foundation = (
        site.foundation_name_bn
        if lang == "bn" and site.foundation_name_bn
        else (site.foundation_name_en or site.site_title)
    )
    foundation_alt = (
        site.foundation_name_en
        if lang == "bn"
        else (site.foundation_name_bn or site.short_name)
    )
    category = donation.category
    if category:
        if lang == "bn":
            category_name = getattr(category, "name_bn", None) or category.name_en
        else:
            category_name = category.name_en
    else:
        category_name = ""
    address = site.address_bn if lang == "bn" and site.address_bn else (site.address_en or site.address_bn)
    return {
        "donation": donation,
        "site_settings": site,
        "language": lang,
        "foundation_name": foundation,
        "foundation_name_alt": foundation_alt,
        "receipt_number": donation.receipt_number or "—",
        "transaction_id": donation.transaction_id or "—",
        "donor_name": donation.display_name,
        "on_behalf_of": donation.on_behalf_of or "",
        "category_name": category_name,
        "amount": donation.amount,
        "currency": donation.currency,
        "payment_method": donation.get_payment_method_display(),
        "donation_date": timezone.localtime(donation.created_at),
        "primary_email": site.primary_email,
        "primary_phone": site.primary_phone,
        "address": address,
        "status_display": donation.get_status_display(),
    }


def generate_receipt_pdf(donation) -> bytes:
    """Generate a professional PDF receipt with embedded Bengali-capable fonts."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    from core.pdf_fonts import escape_pdf_text, pdf_paragraph_styles

    ctx = receipt_context(donation)
    styles = pdf_paragraph_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Receipt {ctx['receipt_number']}",
    )

    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["heading"],
        fontSize=18,
        leading=22,
        spaceAfter=4,
        shaping=1,
    )
    subtitle = ParagraphStyle(
        "ReceiptSub",
        parent=styles["body"],
        fontSize=10,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12,
        shaping=1,
    )
    label_style = styles["label"]
    value_style = styles["body"]

    story = []
    site = ctx["site_settings"]
    if site.site_logo:
        logo_path = Path(site.site_logo.path)
        if logo_path.is_file():
            story.append(Image(str(logo_path), width=36 * mm, height=36 * mm, kind="proportional"))
            story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(escape_pdf_text(ctx["foundation_name"], bold=True), title_style))
    if ctx["foundation_name_alt"] and ctx["foundation_name_alt"] != ctx["foundation_name"]:
        story.append(Paragraph(escape_pdf_text(ctx["foundation_name_alt"]), subtitle))
    story.append(Paragraph(escape_pdf_text(_("Donation Receipt")), subtitle))
    story.append(Spacer(1, 4 * mm))

    rows = [
        [_("Receipt Number"), ctx["receipt_number"]],
        [_("Transaction ID"), ctx["transaction_id"]],
        [_("Date"), ctx["donation_date"].strftime("%d %B %Y, %H:%M")],
        [_("Donor Name"), ctx["donor_name"]],
    ]
    if ctx["on_behalf_of"]:
        rows.append([_("On Behalf Of"), ctx["on_behalf_of"]])
    rows.extend(
        [
            [_("Donation Category"), ctx["category_name"]],
            [_("Donation Amount"), f"{ctx['amount']:g} {ctx['currency']}"],
            [_("Payment Method"), ctx["payment_method"]],
            [_("Status"), ctx["status_display"]],
        ]
    )

    table_data = [
        [
            Paragraph(f"<b>{escape_pdf_text(k)}</b>", label_style),
            Paragraph(escape_pdf_text(v), value_style),
        ]
        for k, v in rows
    ]
    table = Table(table_data, colWidths=[55 * mm, 115 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F7F4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D7D2")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8E4")),
                ("FONTNAME", (0, 0), (-1, -1), styles["font"]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 10 * mm))

    footer_bits = []
    if ctx["address"]:
        footer_bits.append(ctx["address"].replace("\n", ", "))
    if ctx["primary_email"]:
        footer_bits.append(ctx["primary_email"])
    if ctx["primary_phone"]:
        footer_bits.append(ctx["primary_phone"])
    if footer_bits:
        story.append(
            Paragraph(
                escape_pdf_text(" · ".join(footer_bits)),
                styles["small"],
            )
        )
    story.append(
        Paragraph(
            escape_pdf_text(_("Thank you for your generous support.")),
            ParagraphStyle(
                "Thanks",
                parent=styles["body"],
                fontSize=10,
                textColor=colors.HexColor("#0B6B3A"),
                spaceBefore=8,
                shaping=1,
            ),
        )
    )

    doc.build(story)
    return buffer.getvalue()


def receipt_filename(donation) -> str:
    number = donation.receipt_number or donation.transaction_id or str(donation.pk)[:8]
    return f"receipt-{number}.pdf"
