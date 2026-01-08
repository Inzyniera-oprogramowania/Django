from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from pollution_backend.measurements.api.serializers import (
    AggregatedMeasurementSerializer,
)
from pollution_backend.measurements.api.serializers import MeasurementSerializer
from pollution_backend.measurements.models import Measurement
from pollution_backend.selectors.measurements import get_aggregated_measurements
from pollution_backend.selectors.measurements import get_measurements_for_sensor

SENSOR_ID_REQUIRED = "sensor_id query parameter is required."


class MeasurementViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Measurement.objects.none()
    serializer_class = MeasurementSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Measurement.objects.none()

        sensor_id = self.request.query_params.get("sensor_id")
        if not sensor_id:
            return Measurement.objects.none()

        return get_measurements_for_sensor(sensor_id=int(sensor_id))

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
