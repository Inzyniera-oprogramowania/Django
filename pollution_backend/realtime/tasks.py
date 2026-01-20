"""
Celery tasks for real-time data processing.

This module contains Celery tasks for:
- Anomaly detection in sensor measurements
- Alert generation when thresholds are exceeded
"""

import logging
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from pollution_backend.sensors.models import AnomalyLog, QualityNorm, Sensor

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def check_anomaly(
    self,
    sensor_id: int,
    value: float,
    timestamp: str,
) -> dict[str, bool | str | None]:
    """
    Check if a measurement exceeds quality norm thresholds and log anomalies.

    This task compares the measurement value against the applicable QualityNorm
    for the sensor's pollutant. If the value exceeds the threshold, an AnomalyLog
    entry is created.

    Args:
        sensor_id: ID of the sensor that produced the measurement
        value: The measured value
        timestamp: ISO 8601 timestamp of the measurement

    Returns:
        Dictionary with:
            - is_anomaly: bool indicating if threshold was exceeded
            - anomaly_id: ID of created AnomalyLog (if anomaly detected)
            - message: Description of the result

    Business Rules:
        - RB4: System must automatically detect anomalies in measurement data
               and generate appropriate alerts
    """
    try:
        # Get the sensor and its pollutant
        try:
            sensor = Sensor.objects.select_related("pollutant", "monitoring_station").get(
                id=sensor_id
            )
        except Sensor.DoesNotExist:
            logger.warning("Sensor with ID %d not found", sensor_id)
            return {
                "is_anomaly": False,
                "anomaly_id": None,
                "message": f"Sensor {sensor_id} not found",
            }

        pollutant = sensor.pollutant

        # Get applicable quality norms for this pollutant
        today = timezone.now().date()
        quality_norms = QualityNorm.objects.filter(
            pollutant=pollutant,
        ).filter(
            # Norm is valid if:
            # - valid_from is null or <= today
            # - valid_to is null or >= today
            valid_from__lte=today,
        ).filter(
            valid_to__gte=today,
        ) | QualityNorm.objects.filter(
            pollutant=pollutant,
            valid_from__isnull=True,
        ) | QualityNorm.objects.filter(
            pollutant=pollutant,
            valid_to__isnull=True,
        )

        if not quality_norms.exists():
            logger.debug(
                "No quality norms found for pollutant %s",
                pollutant.symbol,
            )
            return {
                "is_anomaly": False,
                "anomaly_id": None,
                "message": f"No quality norms for {pollutant.symbol}",
            }

        # Check against all applicable norms
        for norm in quality_norms:
            if value > norm.threshold_value:
                # Parse timestamp
                detected_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if timezone.is_naive(detected_at):
                    detected_at = timezone.make_aware(detected_at)

                # Create anomaly log entry
                anomaly = AnomalyLog.objects.create(
                    description=(
                        f"Measurement value {value:.2f} {norm.unit} exceeds "
                        f"{norm.norm_type} threshold of {norm.threshold_value:.2f} {norm.unit} "
                        f"for {pollutant.name}"
                    ),
                    detected_at=detected_at,
                    status="detected",
                    sensor=sensor,
                )

                logger.warning(
                    "Anomaly detected: sensor_id=%d, value=%.2f, threshold=%.2f, norm_type=%s",
                    sensor_id,
                    value,
                    norm.threshold_value,
                    norm.norm_type,
                )

                return {
                    "is_anomaly": True,
                    "anomaly_id": anomaly.id,
                    "message": f"Threshold exceeded: {value:.2f} > {norm.threshold_value:.2f}",
                }

        logger.debug(
            "No anomaly detected: sensor_id=%d, value=%.2f within thresholds",
            sensor_id,
            value,
        )
        return {
            "is_anomaly": False,
            "anomaly_id": None,
            "message": "Value within normal range",
        }

    except Exception as e:
        logger.exception("Error checking anomaly for sensor %d: %s", sensor_id, e)
        raise
