import logging
from django.db import transaction
from django.utils import timezone
from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.models import Sensor

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
                
                measurement = Measurement.objects.create(
                    sensor_id=sensor.id,
                    value=value,
                    unit=unit,
                    time=self.data['timestamp']
                )
                
                from pollution_backend.sensors.models import DeviceStatus
                
                DeviceStatus.objects.update_or_create(
                    sensor=sensor,
                    defaults={'updated_at': server_timestamp} 
                )
                
                logger.info(f"Import success: Measurement at {measurement.time} for Sensor {sensor.id}")
                return measurement

        except Exception as e:
            logger.error(f"Import DB Transaction failed: {e}")
            raise e
            