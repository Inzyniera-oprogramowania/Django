from django.urls import path
from .views import MeasurementExportView, ReportIssueCreateView, ReportDownloadView

app_name = "reports"

urlpatterns = [
    path("export/", MeasurementExportView.as_view(), name="export_measurements"),
    path("<int:report_id>/download/", ReportDownloadView.as_view(), name="report_download"),
    path("<int:report_id>/issues/", ReportIssueCreateView.as_view(), name="report_issue_create"),
]