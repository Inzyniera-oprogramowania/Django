from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from pollution_backend.sensors.api.views import AnomalyLogViewSet
from pollution_backend.sensors.api.views import AnomalyRuleViewSet
from pollution_backend.sensors.api.views import DeviceViewSet
from pollution_backend.sensors.api.views import GlobalAnomalyConfigViewSet
from pollution_backend.sensors.api.views import MonitoringStationViewSet
from pollution_backend.sensors.api.views import PollutantViewSet
from pollution_backend.sensors.api.views import QualityNormViewSet
from pollution_backend.sensors.api.views import SensorViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("stations", MonitoringStationViewSet, basename="station")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("devices", DeviceViewSet, basename="device")
router.register("pollutants", PollutantViewSet, basename="pollutant")
router.register("norms", QualityNormViewSet, basename="norm")
router.register("anomalies", AnomalyLogViewSet, basename="anomaly")
router.register("anomaly-rules", AnomalyRuleViewSet, basename="anomaly-rule")
router.register("anomaly-config", GlobalAnomalyConfigViewSet, basename="anomaly-config")

app_name = "sensors"
urlpatterns = router.urls
