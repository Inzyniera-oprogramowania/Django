import pytest
import datetime
from django.utils import timezone
from django.db import IntegrityError, transaction
from pollution_backend.services.measurements import MeasurementImportService
from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.sensors.models import DeviceStatus
from pollution_backend.sensors.tests.factories import SensorFactory
from pollution_backend.users.tests.factories import UserFactory
from pollution_backend.users.models import ApiKey

@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestMeasurementImportService:

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.user = UserFactory()
        self.sensor = SensorFactory(is_active=True)

    def test_process_import_single_success(self):
        timestamp = timezone.now()
        data = {
            "sensor_id": self.sensor.id,
            "value": 25.5,
            "unit": "PM10",
            "timestamp": timestamp
        }
        
        service = MeasurementImportService(data)
        measurement = service.process_import()

        assert measurement.sensor_id == self.sensor.id
        assert measurement.value == 25.5
        assert measurement.time == timestamp
        
        status = DeviceStatus.objects.get(sensor=self.sensor)
        assert status.updated_at is not None

    def test_unit_normalization(self):
        data = {
            "sensor_id": self.sensor.id,
            "value": 10.0,
            "unit": "ug/m3",
            "timestamp": timezone.now()
        }
        service = MeasurementImportService(data)
        measurement = service.process_import()
        
        assert measurement.unit == "µg/m3"

    def test_process_batch_all_success(self):
        base_time = timezone.now()
        initial_count = Measurement.objects.count()
        
        data = [
            {"sensor_id": self.sensor.id, "value": 10, "unit": "PM10", "timestamp": base_time},
            {"sensor_id": self.sensor.id, "value": 20, "unit": "PM10", "timestamp": base_time + datetime.timedelta(minutes=1)},
        ]
        
        MeasurementImportService.process_batch(data, self.user.id, None)
        
        assert Measurement.objects.count() == initial_count + 2
        
        log = SystemLog.objects.filter(event_type="import_success").latest("timestamp")
        assert "2/2" in log.message

    def test_process_batch_partial_failure(self):
        
        base_time = timezone.now()
        
        Measurement.objects.create(
            sensor_id=self.sensor.id,
            value=999,
            unit="PM10",
            time=base_time
        )
        
        initial_count = Measurement.objects.count()
        
        data = [
            {"sensor_id": self.sensor.id, "value": 10, "unit": "PM10", "timestamp": base_time},
            {"sensor_id": self.sensor.id, "value": 20, "unit": "PM10", "timestamp": base_time + datetime.timedelta(minutes=1)},
        ]
        
        MeasurementImportService.process_batch(data, self.user.id, None)
        
        assert Measurement.objects.count() == initial_count + 1
        
        log = SystemLog.objects.filter(event_type="import_success").latest("timestamp")
        assert "1/2" in log.message

    def test_process_batch_rate_limit_exceeded(self):
        api_key = ApiKey.objects.create(user=self.user, limit=5, request_count=5)
        
        initial_count = Measurement.objects.count()
        data = [{"sensor_id": self.sensor.id, "value": 10, "unit": "PM10", "timestamp": timezone.now()}]
        
        MeasurementImportService.process_batch(data, self.user.id, api_key.id)
        
        assert Measurement.objects.count() == initial_count
        
        log = SystemLog.objects.filter(event_type="import_error").latest("timestamp")
        assert "Rate limit exceeded" in log.message

    def test_process_batch_handles_invalid_sensor(self):
        initial_count = Measurement.objects.count()
        data = [
            {"sensor_id": 999999, "value": 10, "unit": "PM10", "timestamp": timezone.now()}
        ]
        
        MeasurementImportService.process_batch(data, self.user.id, None)
        
        assert Measurement.objects.count() == initial_count
        
        log = SystemLog.objects.filter(event_type="import_success").latest("timestamp")
        assert "0/1" in log.message