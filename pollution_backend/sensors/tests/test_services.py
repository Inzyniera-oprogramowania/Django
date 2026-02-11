import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from pollution_backend.services.mqtt import MQTTProcessingService
from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.sensors.models import Sensor, DeviceStatus
from pollution_backend.sensors.tests.factories import (
    SensorFactory,
    MonitoringStationFactory,
    PollutantFactory
)

@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestMQTTProcessingService:
    
    @pytest.fixture
    def sensor(self):
        return SensorFactory(
            is_active=True, 
            sensor_type="PM10", 
            pollutant=PollutantFactory(symbol="PM10")
        )

    def test_process_device_status_updates_status(self, sensor):
        data = {
            "sensor_id": sensor.id,
            "battery_percent": 80,
            "signal_rssi_dbm": -60,
            "uptime_seconds": 3600
        }
        
        MQTTProcessingService.process_device_status(data)
        
        status = DeviceStatus.objects.get(sensor=sensor)
        assert status.battery_percent == 80
        assert status.signal_rssi_dbm == -60
        assert status.uptime_seconds == 3600
        assert sensor.is_active is True

    def test_process_device_status_disables_sensor_on_low_battery(self, sensor):
        data = {
            "sensor_id": sensor.id,
            "battery_percent": 0,
            "signal_rssi_dbm": -90,
            "uptime_seconds": 7200
        }
        
        MQTTProcessingService.process_device_status(data)
        
        sensor.refresh_from_db()
        assert sensor.is_active is False
        assert SystemLog.objects.filter(event_type="BATTERY_CRITICAL", sensor_id=sensor.id).exists()

    def test_process_measurement_creates_entry(self, sensor):
        data = {
            "sensor_id": sensor.id,
            "value": 25.5,
            "unit": "µg/m³",
            "timestamp": timezone.now().isoformat()
        }
        
        with patch("pollution_backend.services.mqtt.check_anomaly.delay") as mock_check:
            count_before = Measurement.objects.count()
            MQTTProcessingService.process_measurement(data)
    
            assert Measurement.objects.count() == count_before + 1
            assert Measurement.objects.filter(sensor_id=sensor.id, value=25.5).exists()
            measurement = Measurement.objects.filter(sensor_id=sensor.id, value=25.5).latest("time")
            assert measurement.sensor_id == sensor.id
            assert measurement.value == 25.5
            mock_check.assert_called_once()

    def test_process_measurement_missing_fields(self, sensor):
        data = {
            "sensor_id": sensor.id,
        }
        
        count_before = Measurement.objects.count()
        MQTTProcessingService.process_measurement(data)
        assert Measurement.objects.count() == count_before

    def test_process_measurement_nonexistent_sensor(self):
        data = {
            "sensor_id": 99999,
            "value": 10.0,
            "timestamp": timezone.now().isoformat()
        }
        count_before = Measurement.objects.count()
        MQTTProcessingService.process_measurement(data)
        assert Measurement.objects.count() == count_before

    def test_process_station_heartbeat(self):
        station = MonitoringStationFactory()
        data = {"status": "ok"}
        
        MQTTProcessingService.process_station_heartbeat(station.station_code, data)
        
        assert SystemLog.objects.filter(event_type="STATION_HEARTBEAT", station_id=station.id).exists()
