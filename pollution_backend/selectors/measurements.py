from django.db.models import Avg
from django.db.models import Max
from django.db.models import Min
from django.db.models.functions import Trunc

from pollution_backend.measurements.models import Measurement


def get_measurements_for_sensor(sensor_id: int):
    return Measurement.objects.filter(sensor_id=sensor_id).order_by("-time")


def get_aggregated_measurements(sensor_id: int, interval: str):
    allowed_intervals = ["minute", "hour", "day", "week", "month", "year"]
    if interval not in allowed_intervals:
        msg = (
            f"Invalid interval '{interval}'. "
            f"Allowed intervals are: {', '.join(allowed_intervals)}"
        )
        raise ValueError(msg)

    queryset = Measurement.objects.filter(sensor_id=sensor_id)

    return (
        queryset.annotate(bucket=Trunc("time", interval))
        .values("bucket")
        .annotate(
            avg_value=Avg("value"),
            min_value=Min("value"),
            max_value=Max("value"),
        )
        .order_by("bucket")[:500]
    )
