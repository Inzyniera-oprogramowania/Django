from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from rest_framework.decorators import action
from pollution_backend.selectors.sensors import get_active_sensors
from pollution_backend.selectors.sensors import get_active_stations
from pollution_backend.selectors.sensors import get_all_stations
from pollution_backend.selectors.sensors import get_norms
from pollution_backend.selectors.sensors import get_pollutants
from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.sensors.models import Pollutant
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.sensors.models import Sensor

from .serializers import MonitoringStationDetailSerializer
from .serializers import MonitoringStationFlatSerializer
from .serializers import MonitoringStationGeoSerializer
from .serializers import PollutantSerializer
from .serializers import QualityNormSerializer
from .serializers import SensorSerializer


from drf_spectacular.utils import extend_schema


class MonitoringStationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MonitoringStation.objects.all()

    @extend_schema(exclude=True)
    def list(self, request, *args, **kwargs):
         return super().list(request, *args, **kwargs)

    @action(detail=False, url_path="all")
    def all_stations(self, request):
        queryset = get_all_stations()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        return get_active_stations()

    def get_object(self):
        station_id = self.kwargs.get("pk")
        return get_object_or_404(get_active_stations(), pk=station_id)

    def get_serializer_class(self):
        if self.action == "list":
            return MonitoringStationGeoSerializer
        if self.action == "all_stations":
            return MonitoringStationFlatSerializer
        return MonitoringStationDetailSerializer


class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer

    def get_queryset(self):
        station_id = self.request.query_params.get("station_id")
        if station_id:
            try:
                station_id = int(station_id)
            except ValueError:
                station_id = None
        else:
            station_id = None
        return get_active_sensors(station_id=station_id)


class PollutantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pollutant.objects.all()
    serializer_class = PollutantSerializer
    pagination_class = None

    def get_queryset(self):
        return get_pollutants()


class QualityNormViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QualityNorm.objects.all()
    serializer_class = QualityNormSerializer
    pagination_class = None

    def get_queryset(self):
        return get_norms()
