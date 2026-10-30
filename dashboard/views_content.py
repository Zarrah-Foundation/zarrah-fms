"""Content modules: News + categories, Transparency (legal docs), and the
Reports export center (PDF / Excel)."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _l

from core.choices import DonationStatus
from dashboard.crud import DashCreateView, DashDeleteView, DashListView, DashUpdateView
from dashboard.forms import NewsCategoryForm, NewsForm, ReportForm
from donations.models import Donation
from finance.models import Expense, Income
from members.models import Member
from news.models import News, NewsCategory
from rbac.permissions import has_action
from reports.models import Report, ReportType


# =========================================================================
# News
# =========================================================================

class NewsList(DashListView):
    model = News
    permission_module = "news"
    ordering = ["-created_at"]
    search_fields = ["title"]
    page_title = _l("News Articles")
    page_icon = "bi-newspaper"
    columns = [
        {"label": _l("Title"), "field": "title"},
        {"label": _l("Category"), "field": "category"},
        {"label": _l("Published"), "field": "is_published"},
        {"label": _l("Publish date"), "field": "published_at"},
    ]
    create_url_name = "dashboard-news-create"
    edit_url_name = "dashboard-news-edit"
    delete_url_name = "dashboard-news-delete"

    def get_queryset(self):
        return super().get_queryset().select_related("category")


class NewsCreate(DashCreateView):
    model = News
    permission_module = "news"
    form_class = NewsForm
    page_title = _l("Add Article")
    success_url_name = "dashboard-news"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class NewsUpdate(DashUpdateView):
    model = News
    permission_module = "news"
    form_class = NewsForm
    page_title = _l("Edit Article")
    success_url_name = "dashboard-news"


class NewsDelete(DashDeleteView):
    model = News
    permission_module = "news"
    success_url_name = "dashboard-news"


class NewsCategoryList(DashListView):
    model = NewsCategory
    permission_module = "news_categories"
    ordering = ["display_order", "name_en"]
    search_fields = ["name_en", "name_bn"]
    page_title = _l("News Categories")
    page_icon = "bi-collection"
    columns = [
        {"label": _l("Name"), "field": "name_en"},
        {"label": _l("Order"), "field": "display_order"},
        {"label": _l("Active"), "field": "is_active"},
    ]
    create_url_name = "dashboard-news-category-create"
    edit_url_name = "dashboard-news-category-edit"
    delete_url_name = "dashboard-news-category-delete"


class NewsCategoryCreate(DashCreateView):
    model = NewsCategory
    permission_module = "news_categories"
    form_class = NewsCategoryForm
    page_title = _l("Add News Category")
    success_url_name = "dashboard-news-categories"


class NewsCategoryUpdate(DashUpdateView):
    model = NewsCategory
    permission_module = "news_categories"
    form_class = NewsCategoryForm
    page_title = _l("Edit News Category")
    success_url_name = "dashboard-news-categories"


class NewsCategoryDelete(DashDeleteView):
    model = NewsCategory
    permission_module = "news_categories"
    success_url_name = "dashboard-news-categories"


# =========================================================================
# Transparency (legal documents over reports.Report)
# =========================================================================

class TransparencyList(DashListView):
    model = Report
    permission_module = "transparency"
    ordering = ["-year", "-created_at"]
    search_fields = ["title", "description"]
    page_title = _l("Transparency documents")
    page_icon = "bi-shield-check"
    columns = [
        {"label": _l("Title"), "field": "title"},
        {"label": _l("Category"), "field": "get_type_display"},
        {"label": _l("Year"), "field": "year"},
        {"label": _l("Public"), "field": "is_public"},
        {"label": _l("Transparency"), "field": "show_on_transparency"},
        {"label": _l("Reports"), "field": "show_on_reports"},
    ]
    create_url_name = "dashboard-transparency-create"
    edit_url_name = "dashboard-transparency-edit"
    delete_url_name = "dashboard-transparency-delete"


class TransparencyCreate(DashCreateView):
    model = Report
    permission_module = "transparency"
    form_class = ReportForm
    page_title = _l("Upload Document")
    success_url_name = "dashboard-transparency"

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)


class TransparencyUpdate(DashUpdateView):
    model = Report
    permission_module = "transparency"
    form_class = ReportForm
    page_title = _l("Edit Document")
    success_url_name = "dashboard-transparency"


class TransparencyDelete(DashDeleteView):
    model = Report
    permission_module = "transparency"
    success_url_name = "dashboard-transparency"


# =========================================================================
# Reports export center (PDF / Excel)
# =========================================================================

@login_required
def reports_center(request):
    if not has_action(request.user, "reports", "view"):
        return redirect("dashboard")
    return render(
        request,
        "dashboard/reports/center.html",
        {
            "can_export": has_action(request.user, "reports", "export"),
            "can_members_bulk_report": has_action(request.user, "members", "bulk_report"),
            "can_applications_bulk_report": has_action(
                request.user, "applications", "bulk_report"
            ),
        },
    )


def _xlsx_response(filename, headers, rows):
    import openpyxl
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def _pdf_response(filename, title, headers, rows):
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from core.pdf_fonts import escape_pdf_text, pdf_paragraph_styles

    styles = pdf_paragraph_styles()
    header_style = ParagraphStyle(
        "ExportHeader",
        parent=styles["body"],
        fontName=styles["font_bold"],
        fontSize=8,
        leading=10,
        textColor=colors.white,
        shaping=1,
    )
    cell_style = ParagraphStyle(
        "ExportCell",
        parent=styles["body"],
        fontSize=8,
        leading=10,
        shaping=1,
    )
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = [
        Paragraph(escape_pdf_text(title, bold=True), styles["title"]),
        Spacer(1, 12),
    ]
    data = [[Paragraph(escape_pdf_text(h), header_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(escape_pdf_text(c), cell_style) for c in row])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6B3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), styles["font"]),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F8")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _donation_rows():
    headers = ["Date", "Donor", "Category", "Amount", "Currency", "Method", "Status"]
    rows = [
        [
            d.created_at.strftime("%Y-%m-%d"),
            d.display_name,
            d.category.name_en if d.category else "",
            d.amount,
            d.currency,
            d.get_payment_method_display(),
            d.get_status_display(),
        ]
        for d in Donation.objects.select_related("category").order_by("-created_at")[:5000]
    ]
    return headers, rows


def _member_rows():
    headers = ["Member ID", "Name", "Phone", "District", "Status", "Joined"]
    rows = [
        [
            m.member_id,
            f"{m.first_name} {m.last_name}",
            m.phone,
            m.district,
            m.get_status_display(),
            m.joined_at.strftime("%Y-%m-%d") if m.joined_at else "",
        ]
        for m in Member.objects.order_by("-created_at")[:5000]
    ]
    return headers, rows


def _finance_rows():
    headers = ["Date", "Type", "Title", "Category/Source", "Amount"]
    rows = []
    for i in Income.objects.all():
        rows.append([i.received_date.strftime("%Y-%m-%d"), "Income", i.title, i.source or "", i.amount])
    for e in Expense.objects.all():
        rows.append([e.expense_date.strftime("%Y-%m-%d"), "Expense", e.title, e.category or "", e.amount])
    rows.sort(key=lambda r: r[0], reverse=True)
    return headers, rows


_DATASETS = {
    "donations": (_donation_rows, "Donations Report"),
    "members": (_member_rows, "Membership Report"),
    "finance": (_finance_rows, "Finance Report"),
}


@login_required
def report_export(request, dataset, fmt):
    if not has_action(request.user, "reports", "export"):
        return redirect("dashboard-reports")
    if dataset not in _DATASETS:
        return redirect("dashboard-reports")
    builder, title = _DATASETS[dataset]
    headers, rows = builder()
    stamp = timezone.now().strftime("%Y%m%d")
    if fmt == "xlsx":
        return _xlsx_response(f"{dataset}-{stamp}.xlsx", headers, rows)
    return _pdf_response(f"{dataset}-{stamp}.pdf", title, headers, rows)
