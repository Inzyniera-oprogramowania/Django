from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from pollution_backend.measurements.api.views import MeasurementViewSet, SystemLogViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("measurements", MeasurementViewSet, basename="measurement")
router.register("logs", SystemLogViewSet, basename="systemlog")

app_name = "measurements"
urlpatterns = router.urls
