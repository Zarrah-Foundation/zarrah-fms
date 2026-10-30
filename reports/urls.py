from django.urls import path

from reports import views

urlpatterns = [
    path("reports/", views.ReportListView.as_view(), name="reports"),
    path("reports/<uuid:pk>/download/", views.ReportDownloadView.as_view(), name="report-download"),
]
