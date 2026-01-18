from django.db.models import QuerySet

from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.sensors.models import Pollutant
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.sensors.models import Sensor


def get_active_stations() -> QuerySet[MonitoringStation]:
    return MonitoringStation.objects.filter(is_active=True).select_related("location")


def get_all_stations() -> QuerySet[MonitoringStation]:
    return MonitoringStation.objects.select_related("location").all()


def get_station_detail(station_id: int) -> MonitoringStation:
    return (
        MonitoringStation.objects.select_related("location")
        .prefetch_related("sensor_set__pollutant")
        .get(pk=station_id)
    )


def get_pollutants() -> QuerySet[Pollutant]:
    return Pollutant.objects.all()


def get_active_sensors(station_id: int | None = None) -> QuerySet[Sensor]:
    queryset = Sensor.objects.filter(is_active=True).select_related(
        "pollutant",
        "monitoring_station",
    )
    if station_id:
        queryset = queryset.filter(monitoring_station_id=station_id)
    return queryset


def get_norms() -> QuerySet[QualityNorm]:
    return QualityNorm.objects.select_related("pollutant").all()
