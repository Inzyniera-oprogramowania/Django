"""
Statistical analysis services for air quality measurements.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
from django.db.models import Avg, Max, Min, StdDev, Count
from django.db.models.functions import TruncDate, TruncHour

from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.models import Sensor, QualityNorm
import logging

logger = logging.getLogger(__name__)


@dataclass
class DescriptiveStats:
    """Container for descriptive statistics results."""
    count: int
    mean: float
    min_value: float
    max_value: float
    std_dev: float
    median: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    unit: str


@dataclass
class TrendAnalysis:
    """Container for trend analysis results."""
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    percent_change: float
    slope: float
    start_avg: float
    end_avg: float
    data_points: list  # List of {time, value} for chart


@dataclass
class PeriodComparison:
    """Container for period comparison results."""
    period1_avg: float
    period2_avg: float
    absolute_diff: float
    percent_diff: float
    period1_max: float
    period2_max: float
    better_period: str  # 'period1' or 'period2'


@dataclass
class NormExceedance:
    """Container for norm exceedance analysis results."""
    total_measurements: int
    exceedances_count: int
    exceedance_percent: float
    norm_value: float
    norm_type: str
    worst_days: list  # List of {date, max_value, avg_value}
    hourly_distribution: list  # Exceedances by hour


def get_descriptive_stats(
    sensor_id: int,
    date_from: datetime,
    date_to: datetime,
) -> Optional[DescriptiveStats]:
    """
    Calculate descriptive statistics for a sensor's measurements.
    """
    queryset = Measurement.objects.filter(
        sensor_id=sensor_id,
        time__gte=date_from,
        time__lte=date_to,
    )

    logger.info(f"DEBUG: Computing stats for sensor {sensor_id} from {date_from} to {date_to}")
    count = queryset.count()
    logger.info(f"DEBUG: Found {count} measurements")

    if not queryset.exists():
        logger.warning("DEBUG: Queryset empty!")
        return None

    # Get basic aggregations from DB
    agg = queryset.aggregate(
        count=Count("value"),
        mean=Avg("value"),
        min_value=Min("value"),
        max_value=Max("value"),
        std_dev=StdDev("value"),
    )

    # Get all values for percentile calculations
    values = list(queryset.values_list("value", flat=True))
    
    if not values:
        return None

    values_array = np.array(values)
    
    # Get unit from first measurement
    unit = queryset.first().unit if queryset.first() else "µg/m³"

    return DescriptiveStats(
        count=agg["count"] or 0,
        mean=round(agg["mean"] or 0, 2),
        min_value=round(agg["min_value"] or 0, 2),
        max_value=round(agg["max_value"] or 0, 2),
        std_dev=round(agg["std_dev"] or 0, 2),
        median=round(float(np.median(values_array)), 2),
        percentile_25=round(float(np.percentile(values_array, 25)), 2),
        percentile_75=round(float(np.percentile(values_array, 75)), 2),
        percentile_95=round(float(np.percentile(values_array, 95)), 2),
        unit=unit,
    )


def get_trend_analysis(
    sensor_id: int,
    date_from: datetime,
    date_to: datetime,
    aggregation: str = "hour",  # 'hour' or 'day'
) -> Optional[TrendAnalysis]:
    """
    Analyze trend in measurements over time.
    """
    queryset = Measurement.objects.filter(
        sensor_id=sensor_id,
        time__gte=date_from,
        time__lte=date_to,
    )

    if not queryset.exists():
        return None

    # Aggregate by time bucket
    if aggregation == "day":
        trunc_func = TruncDate("time")
    else:
        trunc_func = TruncHour("time")

    aggregated = (
        queryset
        .annotate(bucket=trunc_func)
        .values("bucket")
        .annotate(avg_value=Avg("value"))
        .order_by("bucket")
    )

    data_points = [
        {"time": item["bucket"].isoformat(), "value": round(item["avg_value"], 2)}
        for item in aggregated
    ]

    if len(data_points) < 2:
        return TrendAnalysis(
            trend_direction="stable",
            percent_change=0,
            slope=0,
            start_avg=data_points[0]["value"] if data_points else 0,
            end_avg=data_points[0]["value"] if data_points else 0,
            data_points=data_points,
        )

    # Calculate linear regression for trend
    values = [p["value"] for p in data_points]
    x = np.arange(len(values))
    y = np.array(values)
    
    # Linear fit
    slope, intercept = np.polyfit(x, y, 1)
    
    # Calculate averages for first and last 10% of data
    chunk_size = max(1, len(values) // 10)
    start_avg = np.mean(values[:chunk_size])
    end_avg = np.mean(values[-chunk_size:])
    
    # Calculate percent change
    if start_avg != 0:
        percent_change = ((end_avg - start_avg) / start_avg) * 100
    else:
        percent_change = 0

    # Determine trend direction
    threshold = 5  # 5% change threshold
    if percent_change > threshold:
        trend_direction = "increasing"
    elif percent_change < -threshold:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    return TrendAnalysis(
        trend_direction=trend_direction,
        percent_change=round(percent_change, 2),
        slope=round(slope, 4),
        start_avg=round(start_avg, 2),
        end_avg=round(end_avg, 2),
        data_points=data_points,
    )


def get_period_comparison(
    sensor_id: int,
    period1_from: datetime,
    period1_to: datetime,
    period2_from: datetime,
    period2_to: datetime,
) -> Optional[PeriodComparison]:
    """
    Compare two time periods for a sensor.
    """
    def get_period_stats(from_dt, to_dt):
        qs = Measurement.objects.filter(
            sensor_id=sensor_id,
            time__gte=from_dt,
            time__lte=to_dt,
        )
        return qs.aggregate(
            avg=Avg("value"),
            max_val=Max("value"),
        )

    stats1 = get_period_stats(period1_from, period1_to)
    stats2 = get_period_stats(period2_from, period2_to)

    if stats1["avg"] is None or stats2["avg"] is None:
        return None

    avg1 = stats1["avg"]
    avg2 = stats2["avg"]
    
    absolute_diff = avg2 - avg1
    percent_diff = ((avg2 - avg1) / avg1 * 100) if avg1 != 0 else 0
    
    # Lower values are better for pollution
    better_period = "period1" if avg1 < avg2 else "period2"

    return PeriodComparison(
        period1_avg=round(avg1, 2),
        period2_avg=round(avg2, 2),
        absolute_diff=round(absolute_diff, 2),
        percent_diff=round(percent_diff, 2),
        period1_max=round(stats1["max_val"] or 0, 2),
        period2_max=round(stats2["max_val"] or 0, 2),
        better_period=better_period,
    )


def get_norm_exceedance_analysis(
    sensor_id: int,
    date_from: datetime,
    date_to: datetime,
) -> Optional[NormExceedance]:
    """
    Analyze how often measurements exceed quality norms.
    """
    # Get sensor and its pollutant
    try:
        sensor = Sensor.objects.select_related("pollutant").get(id=sensor_id)
    except Sensor.DoesNotExist:
        return None

    # Get applicable norm
    norm = QualityNorm.objects.filter(
        pollutant=sensor.pollutant,
    ).first()

    if not norm:
        return None

    queryset = Measurement.objects.filter(
        sensor_id=sensor_id,
        time__gte=date_from,
        time__lte=date_to,
    )

    total = queryset.count()
    if total == 0:
        return None

    exceedances = queryset.filter(value__gt=norm.threshold_value).count()
    exceedance_percent = (exceedances / total) * 100

    # Find worst days
    daily_stats = (
        queryset
        .annotate(date=TruncDate("time"))
        .values("date")
        .annotate(
            max_value=Max("value"),
            avg_value=Avg("value"),
        )
        .order_by("-max_value")[:5]
    )

    worst_days = [
        {
            "date": item["date"].isoformat(),
            "max_value": round(item["max_value"], 2),
            "avg_value": round(item["avg_value"], 2),
        }
        for item in daily_stats
    ]

    # Hourly distribution of exceedances
    hourly_exceedances = (
        queryset
        .filter(value__gt=norm.threshold_value)
        .annotate(hour=TruncHour("time"))
        .extra(select={"hour_of_day": "EXTRACT(HOUR FROM time)"})
        .values("hour_of_day")
        .annotate(count=Count("value"))
        .order_by("hour_of_day")
    )

    hourly_distribution = [
        {"hour": int(item["hour_of_day"]), "count": item["count"]}
        for item in hourly_exceedances
    ]

    return NormExceedance(
        total_measurements=total,
        exceedances_count=exceedances,
        exceedance_percent=round(exceedance_percent, 2),
        norm_value=norm.threshold_value,
        norm_type=norm.norm_type,
        worst_days=worst_days,
        hourly_distribution=hourly_distribution,
    )
