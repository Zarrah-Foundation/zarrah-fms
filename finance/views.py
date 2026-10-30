from collections import OrderedDict

from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from finance.models import FinancialSummary, MonthlyFinancialSummary
from reports.models import Report, ReportType


# Public transparency document center groups (not private ledgers).
GOVERNANCE_LEGAL_TYPES = [
    ReportType.CONSTITUTION,
    ReportType.REGISTRATION,
    ReportType.LEGAL,
    ReportType.GOVERNANCE,
    ReportType.POLICY,
    ReportType.BOARD,
]

FINANCIAL_DOC_TYPES = [
    ReportType.FINANCIAL,
    ReportType.ANNUAL,
    ReportType.AUDIT,
]

PUBLIC_REPORT_TYPES = [
    ReportType.ACTIVITY,
    ReportType.OTHER,
]


def _group_documents(reports, type_list):
    grouped = OrderedDict((t, []) for t in type_list)
    labels = dict(ReportType.choices)
    remaining = []
    for report in reports:
        if report.type in grouped:
            grouped[report.type].append(report)
        else:
            remaining.append(report)
    result = [
        {"type": rtype, "label": labels.get(rtype, rtype), "documents": items}
        for rtype, items in grouped.items()
        if items
    ]
    if remaining:
        result.append(
            {
                "type": "OTHER",
                "label": labels.get(ReportType.OTHER, _("Other")),
                "documents": remaining,
            }
        )
    return result


class TransparencyView(TemplateView):
    """Public transparency / accountability document center."""

    template_name = "finance/transparency.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["yearly_summaries"] = FinancialSummary.objects.filter(
            is_published=True
        ).order_by("-year")
        ctx["monthly_summaries"] = MonthlyFinancialSummary.objects.filter(
            is_published=True
        ).order_by("-year", "-month")[:24]

        reports = Report.objects.filter(
            is_public=True, show_on_transparency=True
        ).order_by("display_order", "-published_at", "-year", "-created_at")

        # Split into thematic blocks for the document center.
        gov = [r for r in reports if r.type in GOVERNANCE_LEGAL_TYPES]
        fin = [r for r in reports if r.type in FINANCIAL_DOC_TYPES]
        other = [
            r
            for r in reports
            if r.type not in GOVERNANCE_LEGAL_TYPES and r.type not in FINANCIAL_DOC_TYPES
        ]

        ctx["governance_groups"] = _group_documents(gov, GOVERNANCE_LEGAL_TYPES)
        ctx["financial_doc_groups"] = _group_documents(fin, FINANCIAL_DOC_TYPES)
        ctx["other_transparency_groups"] = _group_documents(other, PUBLIC_REPORT_TYPES)
        # Backward-compatible flat groups for any older template hooks.
        all_types = GOVERNANCE_LEGAL_TYPES + FINANCIAL_DOC_TYPES + PUBLIC_REPORT_TYPES
        ctx["document_groups"] = _group_documents(list(reports), all_types)
        from pages.organization_data import FINANCIAL_PRINCIPLES, TRANSPARENCY_PAGE

        ctx["transparency_page"] = TRANSPARENCY_PAGE
        ctx["financial_principles"] = FINANCIAL_PRINCIPLES
        return ctx
