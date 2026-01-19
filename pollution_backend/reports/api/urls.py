from django.urls import path
from .views import MeasurementExportView

app_name = "reports"

urlpatterns = [
    path("export/", MeasurementExportView.as_view(), name="export_measurements"),
]