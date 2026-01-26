from django_filters import rest_framework as filters
from pollution_backend.measurements.models import Measurement

class MeasurementFilter(filters.FilterSet):
    date_from = filters.DateTimeFilter(field_name="time", lookup_expr="gte")
    date_to = filters.DateTimeFilter(field_name="time", lookup_expr="lte")
    sensor_id = filters.NumberFilter(field_name="sensor_id")

    class Meta:
        model = Measurement
        fields = ["sensor_id", "date_from", "date_to"]
