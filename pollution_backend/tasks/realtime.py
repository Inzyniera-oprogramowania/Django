import logging
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from pollution_backend.sensors.models import AnomalyLog, AnomalyRule, Sensor

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
    try:
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

        rule = AnomalyRule.objects.filter(
            pollutant=pollutant,
            is_enabled=True,
        ).first()

        if not rule:
            logger.debug(
                "No detection rule found/enabled for pollutant %s",
                pollutant.symbol,
            )
            return {
                "is_anomaly": False,
                "anomaly_id": None,
                "message": f"No rule for {pollutant.symbol}",
            }

        is_anomaly = False
        anomaly_desc = ""
        anomaly_severity = "warning"

        if value > rule.critical_threshold:
            is_anomaly = True
            anomaly_severity = "critical"
            anomaly_desc = (
                f"CRITICAL: Value {value:.2f} exceeds critical threshold "
                f"of {rule.critical_threshold:.2f} for {pollutant.symbol}"
            )
        elif value > rule.warning_threshold:
            is_anomaly = True
            anomaly_severity = "warning"
            anomaly_desc = (
                f"WARNING: Value {value:.2f} exceeds warning threshold "
                f"of {rule.warning_threshold:.2f} for {pollutant.symbol}"
            )

        if is_anomaly:
            detected_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timezone.is_naive(detected_at):
                detected_at = timezone.make_aware(detected_at)

            anomaly = AnomalyLog.objects.create(
                description=anomaly_desc,
                detected_at=detected_at,
                status="pending",  
                severity=anomaly_severity,
                sensor=sensor,
            )

            logger.warning(
                "Anomaly detected: sensor_id=%d, value=%.2f, severity=%s",
                sensor_id,
                value,
                anomaly_severity,
            )

            return {
                "is_anomaly": True,
                "anomaly_id": anomaly.id,
                "message": anomaly_desc,
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
