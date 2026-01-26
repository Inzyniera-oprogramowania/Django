import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Max
from pollution_backend.sensors.models import MonitoringStation, Sensor
from pollution_backend.measurements.models import Measurement, SystemLog

class Command(BaseCommand):
    help = "Periodically updates is_active status for stations and sensors based on recent activity."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=300,
            help="Interval in seconds between checks (default: 300s / 5m)",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=48,
            help="Inactivity timeout in hours (default: 48h)",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        timeout_hours = options["timeout"]
        
        self.stdout.write(self.style.SUCCESS(f"Starting status monitor (Interval: {interval}s, Timeout: {timeout_hours}h)"))

        while True:
            try:
                self.update_statuses(timeout_hours)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during update: {e}"))
            
            time.sleep(interval)

    def update_statuses(self, timeout_hours):
        now = timezone.now()
        threshold = now - timedelta(hours=timeout_hours)
        
        from pollution_backend.realtime.sensors import broadcast_sensor_log, broadcast_station_log

        sensors = Sensor.objects.all()
        for sensor in sensors:
            latest_meas = Measurement.objects.using("timeseries").filter(sensor_id=sensor.id).aggregate(latest=Max("time"))["latest"]
            latest_log = SystemLog.objects.filter(sensor_id=sensor.id).aggregate(latest=Max("timestamp"))["latest"]
            
            latest_activity = None
            if latest_meas and latest_log:
                latest_activity = max(latest_meas, latest_log)
            elif latest_meas:
                latest_activity = latest_meas
            elif latest_log:
                latest_activity = latest_log
            
            is_active = False
            if latest_activity and latest_activity >= threshold:
                is_active = True
                
            if sensor.is_active != is_active:
                self.stdout.write(f"Updating Sensor {sensor.id} active state: {sensor.is_active} -> {is_active}")
                sensor.is_active = is_active
                sensor.save()

                event = "DEVICE_ONLINE" if is_active else "DEVICE_OFFLINE"
                msg = f"Sensor {sensor.id} is now {'ACTIVE' if is_active else 'INACTIVE'} (Last activity: {latest_activity})"
                log = SystemLog.objects.create(
                    event_type=event,
                    message=msg,
                    log_level=SystemLog.INFO if is_active else SystemLog.ERROR,
                    sensor_id=sensor.id
                )
                broadcast_sensor_log(sensor.id, log)

        stations = MonitoringStation.objects.all()
        for station in stations:
            latest_activity = SystemLog.objects.filter(station_id=station.id).aggregate(latest=Max("timestamp"))["latest"]
                
            is_active = False
            if latest_activity and latest_activity >= threshold:
                is_active = True
                
            if station.is_active != is_active:
                self.stdout.write(f"Updating Station {station.station_code} active state: {station.is_active} -> {is_active}")
                station.is_active = is_active
                station.save()

                event = "STATION_ONLINE" if is_active else "STATION_OFFLINE"
                msg = f"Station {station.station_code} is now {'ACTIVE' if is_active else 'INACTIVE'} (Last activity: {latest_activity})"
                log = SystemLog.objects.create(
                    event_type=event,
                    message=msg,
                    log_level=SystemLog.INFO if is_active else SystemLog.ERROR,
                    station_id=station.id
                )
                broadcast_station_log(station.id, log)
