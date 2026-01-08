from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from pollution_backend.measurements.api.views import MeasurementViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("measurements", MeasurementViewSet, basename="measurement")

app_name = "measurements"
urlpatterns = router.urls
