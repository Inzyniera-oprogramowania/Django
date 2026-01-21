from datetime import datetime

from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from pollution_backend.measurements.api.serializers import (
    AggregatedMeasurementSerializer,
)
from pollution_backend.measurements.api.serializers import MeasurementSerializer
from pollution_backend.measurements.models import Measurement
from pollution_backend.selectors.measurements import get_aggregated_measurements
from pollution_backend.selectors.measurements import get_measurements_for_sensor

SENSOR_ID_REQUIRED = "sensor_id query parameter is required."


class MeasurementPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class MeasurementViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Measurement.objects.none()
    serializer_class = MeasurementSerializer
    pagination_class = MeasurementPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Measurement.objects.none()

        sensor_id = self.request.query_params.get("sensor_id")
        if not sensor_id:
            return Measurement.objects.none()

        date_from = self._parse_date(self.request.query_params.get("date_from"))
        date_to = self._parse_date(self.request.query_params.get("date_to"))

        return get_measurements_for_sensor(
            sensor_id=int(sensor_id),
            date_from=date_from,
            date_to=date_to,
        )

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    @action(detail=False, methods=["get"])
    def aggregated(self, request):
        sensor_id = request.query_params.get("sensor_id")
        interval = request.query_params.get("interval", "hour")
        if not sensor_id:
            raise ValidationError(SENSOR_ID_REQUIRED)

        try:
            data = get_aggregated_measurements(
                sensor_id=int(sensor_id),
                interval=interval,
            )
        except ValueError as err:
            raise ValidationError(str(err)) from err

        serializer = AggregatedMeasurementSerializer(data, many=True)
        return Response(serializer.data)


class SystemLogViewSet(viewsets.ModelViewSet):
    from pollution_backend.measurements.models import SystemLog
    from pollution_backend.measurements.api.serializers import SystemLogSerializer
    
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    pagination_class = None
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by device
        sensor_id = self.request.query_params.get('sensor_id')
        station_id = self.request.query_params.get('station_id')
        
        if sensor_id:
            queryset = queryset.filter(sensor_id=sensor_id)
        if station_id:
            queryset = queryset.filter(station_id=station_id)
            
        return queryset

