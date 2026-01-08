from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from pollution_backend.selectors.sensors import get_active_sensors
from pollution_backend.selectors.sensors import get_active_stations
from pollution_backend.selectors.sensors import get_norms
from pollution_backend.selectors.sensors import get_pollutants
from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.sensors.models import Pollutant
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.sensors.models import Sensor

from .serializers import MonitoringStationDetailSerializer
from .serializers import MonitoringStationGeoSerializer
from .serializers import PollutantSerializer
from .serializers import QualityNormSerializer
from .serializers import SensorSerializer


class MonitoringStationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MonitoringStation.objects.all()
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_active_stations()

    def get_object(self):
        station_id = self.kwargs.get("pk")
        return get_object_or_404(get_active_stations(), pk=station_id)

    def get_serializer_class(self):
        if self.action == "list":
            return MonitoringStationGeoSerializer
        return MonitoringStationDetailSerializer


class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        station_id = self.request.query_params.get("station_id")
        return get_active_sensors(station_id=station_id)


class PollutantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pollutant.objects.all()
    serializer_class = PollutantSerializer
    pagination_class = None
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_pollutants()


class QualityNormViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QualityNorm.objects.all()
    serializer_class = QualityNormSerializer
    pagination_class = None
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_norms()
