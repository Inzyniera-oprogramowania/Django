import logging
from datetime import datetime
from django.utils import timezone
from django.conf import settings

from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.sensors.models import Sensor, DeviceStatus, MonitoringStation
from pollution_backend.realtime.sensors import (
    broadcast_sensor_status, 
    broadcast_station_log, 
    broadcast_sensor_log
)
from pollution_backend.tasks.realtime import check_anomaly

logger = logging.getLogger(__name__)

class MQTTProcessingService:
    @staticmethod
    def process_measurement(data: dict):
        try:
            sensor_id = data.get("sensor_id")
            value = data.get("value")
            unit = data.get("unit", "µg/m³")
            timestamp_str = data.get("timestamp")

            if not all([sensor_id, value is not None, timestamp_str]):
                logger.error("Missing fields in measurement: %s", data)
                return

            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if timezone.is_naive(timestamp):
                timestamp = timezone.make_aware(timestamp)
            if not Sensor.objects.filter(id=sensor_id).exists():
                logger.warning("Sensor ID %s not found", sensor_id)
                return

            measurement = Measurement.objects.create(
                time=timestamp,
                sensor_id=sensor_id,
                value=value,
                unit=unit
            )

            check_anomaly.delay(sensor_id=sensor_id, value=value, timestamp=timestamp_str)

            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"sensor_{sensor_id}_status",
                    {
                        "type": "measurement",
                        "data": {
                            "msg_type": "measurement",
                            "sensor_id": sensor_id,
                            "value": value,
                            "unit": unit,
                            "timestamp": timestamp.isoformat(),
                        },
                    },
                )
            
            logger.info(f"Processed measurement for Sensor {sensor_id}: {value}")

        except Exception as e:
            logger.exception("Error in process_measurement: %s", e)

    @staticmethod
    def process_device_status(data: dict):
        sensor_id = data.get("sensor_id")
        if not sensor_id:
            return

        try:
            sensor = Sensor.objects.get(id=sensor_id)
        except Sensor.DoesNotExist:
            return

        battery = data.get("battery_percent", 100)
        rssi = data.get("signal_rssi_dbm", -50)
        uptime = data.get("uptime_seconds", 0)

        if battery == 0 and sensor.is_active:
            sensor.is_active = False
            sensor.save()
            
            log = SystemLog.objects.create(
                event_type="BATTERY_CRITICAL",
                message=f"Sensor {sensor_id} disabled (0% battery)",
                log_level=SystemLog.WARNING,
                sensor_id=sensor_id
            )
            broadcast_sensor_log(sensor_id, log)

        status, _ = DeviceStatus.objects.update_or_create(
            sensor=sensor,
            defaults={
                "battery_percent": battery,
                "signal_rssi_dbm": rssi,
                "uptime_seconds": uptime,
            },
        )

        log = SystemLog.objects.create(
            event_type="SENSOR_STATUS",
            message=f"Sensor {sensor_id} status updated (Battery: {battery}%, Signal: {rssi} dBm)",
            log_level=SystemLog.INFO,
            sensor_id=sensor_id
        )
        broadcast_sensor_log(sensor_id, log)

        broadcast_sensor_status(sensor_id, {
            "msg_type": "status",
            "sensor_id": sensor_id,
            "battery_percent": status.battery_percent,
            "signal_rssi_dbm": status.signal_rssi_dbm,
            "uptime_seconds": status.uptime_seconds,
            "updated_at": status.updated_at.isoformat(),
        })

    @staticmethod
    def process_station_heartbeat(station_code: str, data: dict):
        try:
            station = MonitoringStation.objects.get(station_code=station_code)
            
            log = SystemLog.objects.create(
                station_id=station.id,
                event_type="STATION_HEARTBEAT",
                message=f"Station {station_code} heartbeat received",
                log_level=SystemLog.INFO
            )
            broadcast_station_log(station.id, log)
            
        except MonitoringStation.DoesNotExist:
            logger.warning(f"Heartbeat from unknown station: {station_code}")