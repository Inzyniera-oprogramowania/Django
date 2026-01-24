from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from pollution_backend.measurements.api.views import MeasurementViewSet, SystemLogViewSet, MeasurementImportView

app_name = "measurements"

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("measurements", MeasurementViewSet, basename="measurement")
router.register("logs", SystemLogViewSet, basename="systemlog")

urlpatterns = [
    path("measurements/import/", MeasurementImportView.as_view(), name="measurement-import"),
]

urlpatterns += router.urls