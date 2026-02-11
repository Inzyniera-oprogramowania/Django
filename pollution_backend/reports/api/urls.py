from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, MeasurementExportView, ReportIssueCreateView, ReportDownloadView

app_name = "reports"

router = DefaultRouter()
router.register(r'', ReportViewSet, basename='report')

urlpatterns = [
    path("export/", MeasurementExportView.as_view(), name="export_measurements"),
    path("<int:report_id>/download/", ReportDownloadView.as_view(), name="report_download"),
    path("<int:report_id>/issues/", ReportIssueCreateView.as_view(), name="report_issue_create"),
    path("", include(router.urls)),
]
