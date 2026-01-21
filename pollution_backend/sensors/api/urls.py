from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from pollution_backend.sensors.api.views import DeviceViewSet
from pollution_backend.sensors.api.views import MonitoringStationViewSet
from pollution_backend.sensors.api.views import PollutantViewSet
from pollution_backend.sensors.api.views import QualityNormViewSet
from pollution_backend.sensors.api.views import SensorViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("stations", MonitoringStationViewSet, basename="station")
router.register("sensors", SensorViewSet, basename="sensor")
router.register("pollutants", PollutantViewSet, basename="pollutant")
router.register("norms", QualityNormViewSet, basename="norm")
router.register("devices", DeviceViewSet, basename="device")

app_name = "sensors"
urlpatterns = router.urls
