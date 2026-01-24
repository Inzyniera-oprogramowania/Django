from django.urls import path
from .views import MeasurementExportView, ReportIssueCreateView

app_name = "reports"

urlpatterns = [
    path("export/", MeasurementExportView.as_view(), name="export_measurements"),
    path("reports/<int:report_id>/issues/", ReportIssueCreateView.as_view(), name="report_issue_create"),
]