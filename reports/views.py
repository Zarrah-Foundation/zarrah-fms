from collections import OrderedDict

from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from reports.models import Report, ReportType

REPORT_SECTION_ORDER = [
    ReportType.ANNUAL,
    ReportType.ACTIVITY,
    ReportType.AUDIT,
    ReportType.OTHER,
]


def _group_reports(reports):
    labels = dict(ReportType.choices)
    grouped = OrderedDict((t, []) for t in REPORT_SECTION_ORDER)
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
        # Preserve type order for leftover categories with content.
        other_map = OrderedDict()
        for report in remaining:
            other_map.setdefault(report.type, []).append(report)
        for rtype, items in other_map.items():
            result.append(
                {
                    "type": rtype,
                    "label": labels.get(rtype, rtype),
                    "documents": items,
                }
            )
    return result


class ReportListView(ListView):
    model = Report
    template_name = "reports/list.html"
    context_object_name = "reports"
    paginate_by = 40

    def get_queryset(self):
        return Report.objects.filter(
            is_public=True, show_on_reports=True
        ).order_by("display_order", "-year", "-published_at", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page_reports = list(ctx.get("reports") or [])
        ctx["report_groups"] = _group_reports(page_reports)
        from pages.organization_data import REPORTS_PAGE

        ctx["reports_page"] = REPORTS_PAGE
        return ctx


class ReportDownloadView(DetailView):
    model = Report
    pk_url_kwarg = "pk"

    def get(self, request, pk):
        report = get_object_or_404(Report, pk=pk, is_public=True)
        if not (report.show_on_transparency or report.show_on_reports):
            raise Http404
        Report.objects.filter(pk=pk).update(download_count=F("download_count") + 1)
        if not report.file:
            raise Http404
        filename = report.file.name.split("/")[-1]
        return FileResponse(
            report.file.open("rb"), as_attachment=True, filename=filename
        )
