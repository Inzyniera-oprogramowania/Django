from django.urls import path

from .views import SensorDetailView
from .views import SensorHistoryView
from .views import SensorLatestMeasurementView
from .views import SensorListView

app_name = "sensors"

urlpatterns = [
    # /api/sensors/
    path("", SensorListView.as_view(), name="sensor-list"),
    # /api/sensors/1/
    path("<int:sensor_id>/", SensorDetailView.as_view(), name="sensor-detail"),
    # /api/sensors/1/latest/
    path(
        "<int:sensor_id>/latest/",
        SensorLatestMeasurementView.as_view(),
        name="sensor-latest",
    ),
    # /api/sensors/1/history/
    path(
        "<int:sensor_id>/history/",
        SensorHistoryView.as_view(),
        name="sensor-history",
    ),
]
