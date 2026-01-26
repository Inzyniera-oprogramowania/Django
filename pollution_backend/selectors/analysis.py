from django.shortcuts import get_object_or_404
from pollution_backend.sensors.models import Sensor

def get_sensor_with_details(sensor_id: int) -> Sensor:
    return get_object_or_404(
        Sensor.objects.select_related(
            "pollutant",
            "monitoring_station",
            "monitoring_station__location"
        ),
        pk=sensor_id
    )