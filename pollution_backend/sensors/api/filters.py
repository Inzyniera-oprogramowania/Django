from django_filters import rest_framework as filters
from pollution_backend.sensors.models import AnomalyLog

class AnomalyLogFilter(filters.FilterSet):
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