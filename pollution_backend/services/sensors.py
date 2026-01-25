from django.utils import timezone
from pollution_backend.sensors.models import DeviceStatus
from pollution_backend.measurements.models import SystemLog
from pollution_backend.realtime.sensors import (
    broadcast_sensor_status, 
    publish_mqtt_command, 
    broadcast_sensor_log,
    broadcast_station_log
)
from pollution_backend.services.redis_cache import DeviceListCache

class SensorService:
    @staticmethod
    def reset_sensor(sensor):
        status, _ = DeviceStatus.objects.get_or_create(sensor=sensor)
        status.uptime_seconds = 0
        status.last_reset_at = timezone.now()
        status.save()

        broadcast_sensor_status(sensor.id, {
            "sensor_id": sensor.id,
            "uptime_seconds": 0,
            "last_reset_at": status.last_reset_at.isoformat(),
            "reset": True,
            "battery_percent": 100,
        })

        SystemLog.objects.create(
            event_type="DEVICE_RESET",
            message=f"Device reset triggered for Sensor {sensor.id}",
            log_level=SystemLog.WARNING,
            sensor_id=sensor.id,
        )

        if sensor.monitoring_station:
            publish_mqtt_command(sensor.monitoring_station.station_code, '{"command": "RESET"}')

        return status

    @staticmethod
    def log_sensor_action(sensor, action_type, message, level):
        log = SystemLog.objects.create(
            sensor_id=sensor.id,
            station_id=sensor.monitoring_station.id if sensor.monitoring_station else None,
            event_type=action_type,
            message=message,
            log_level=level
        )
        broadcast_sensor_log(sensor.id, log)
        if sensor.monitoring_station:
            broadcast_station_log(sensor.monitoring_station.id, log)
        return log

    @staticmethod
    def invalidate_device_list_cache():
        DeviceListCache.invalidate()