import logging
from django.db import transaction
from django.utils import timezone
from pollution_backend.sensors.models import Sensor
from pollution_backend.measurements.models import SystemLog, Measurement
from pollution_backend.users.models import User, ApiKey
from django.db.models import F
from django.db import IntegrityError
from pollution_backend.sensors.models import DeviceStatus

logger = logging.getLogger(__name__)

class MeasurementImportService:
    def __init__(self, validated_data):
        self.data = validated_data

    def process_import(self):
        value = self.data['value']
        unit = self.data['unit']
        
        if unit == 'ug/m3':
            unit = 'µg/m3'
            
        server_timestamp = timezone.now()

        try:
            with transaction.atomic():
                sensor = Sensor.objects.get(id=self.data['sensor_id'])
                
                with transaction.atomic(using='timeseries'):
                    measurement = Measurement.objects.create(
                        sensor_id=sensor.id,
                        value=value,
                        unit=unit,
                        time=self.data['timestamp']
                    )
                
                DeviceStatus.objects.update_or_create(
                    sensor=sensor,
                    defaults={'updated_at': server_timestamp} 
                )
                
                logger.info(f"Import success: Measurement at {measurement.time} for Sensor {sensor.id}")
                return measurement

        except Exception as e:
            logger.error(f"Import DB Transaction failed: {e}")
            raise e

    @staticmethod
    def process_batch(items: list, user_id: int | None, api_key_id: int | None):
        
        user = User.objects.get(pk=user_id) if user_id else None
        
        if api_key_id:
            updated = ApiKey.objects.filter(
                pk=api_key_id, 
                request_count__lt=F('limit')
            ).update(request_count=F('request_count') + 1)
            
            if updated == 0:
                SystemLog.objects.create(
                    event_type="import_error",
                    message="Rate limit exceeded during async processing.",
                    log_level=SystemLog.ERROR,
                    user=user
                )
                return

        success_count = 0
        timestamp = timezone.now()
        first_sensor_id = items[0]['sensor_id'] if items else None
        
        try:
            for item in items:
                try:
                    service = MeasurementImportService(item)
                    service.process_import()
                    success_count += 1
                except IntegrityError:
                    continue  
                except Exception as e:
                    logger.error(f"Error processing item: {e}")

            if len(items) > 1 or success_count == 0:
                msg = f"Batch imported {success_count}/{len(items)} measurements."
            else:
                msg = f"Imported measurement for sensor {first_sensor_id}."

            SystemLog.objects.create(
                event_type="import_success",
                message=msg,
                log_level=SystemLog.SUCCESS,
                sensor_id=first_sensor_id,
                user=user
            )

        except Exception as e:
            SystemLog.objects.create(
                event_type="import_error",
                message=f"Async processing failed: {str(e)}",
                log_level=SystemLog.ERROR,
                user=user
            )