from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from pollution_backend.selectors.sensors import get_active_sensors
from pollution_backend.selectors.sensors import get_active_stations
from pollution_backend.selectors.sensors import get_all_stations
from pollution_backend.selectors.sensors import get_norms
from pollution_backend.selectors.sensors import get_pollutants
from pollution_backend.sensors.models import AnomalyLog
from pollution_backend.sensors.models import AnomalyRule
from pollution_backend.sensors.models import GlobalAnomalyConfig
from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.sensors.models import Pollutant
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.sensors.models import Sensor

from .serializers import AnomalyLogSerializer
from .serializers import AnomalyRuleSerializer
from .serializers import GlobalAnomalyConfigSerializer
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


class AnomalyLogFilter(filters.FilterSet):
    """Filter for AnomalyLog queryset."""

    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    sensor_id = filters.NumberFilter(field_name="sensor_id")
    detected_at_after = filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="gte"
    )
    detected_at_before = filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="lte"
    )

    class Meta:
        model = AnomalyLog
        fields = ["status", "sensor_id", "detected_at_after", "detected_at_before"]


class AnomalyLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AnomalyLog model.

    Supports:
    - GET /api/anomalies/ - list with filtering
    - GET /api/anomalies/{id}/ - single anomaly details
    - PATCH /api/anomalies/{id}/ - update status
    """

    queryset = AnomalyLog.objects.all()
    serializer_class = AnomalyLogSerializer
    filterset_class = AnomalyLogFilter
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["detected_at", "status", "sensor__id"]
    ordering = ["-detected_at"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return AnomalyLog.objects.select_related(
            "sensor",
            "sensor__monitoring_station",
            "sensor__pollutant",
        )


class AnomalyRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AnomalyRule model.

    Supports:
    - GET /api/anomaly-rules/ - list all rules
    - GET /api/anomaly-rules/{id}/ - single rule details
    - PUT/PATCH /api/anomaly-rules/{id}/ - update rule
    """

    queryset = AnomalyRule.objects.all()
    serializer_class = AnomalyRuleSerializer
    pagination_class = None
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return AnomalyRule.objects.select_related("pollutant").order_by("pollutant__symbol")


class GlobalAnomalyConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for GlobalAnomalyConfig (singleton).

    Supports:
    - GET /api/anomaly-config/ - get global config
    - PUT/PATCH /api/anomaly-config/1/ - update global config
    """

    queryset = GlobalAnomalyConfig.objects.all()
    serializer_class = GlobalAnomalyConfigSerializer
    pagination_class = None
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        # Ensure singleton exists
        GlobalAnomalyConfig.get_config()
        return GlobalAnomalyConfig.objects.all()



