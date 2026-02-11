import pytest
from unittest.mock import patch, MagicMock
from pollution_backend.selectors.devices import get_aggregated_device_list
from pollution_backend.services.sensors import SensorService
from pollution_backend.measurements.models import SystemLog
from pollution_backend.sensors.models import DeviceStatus
from pollution_backend.sensors.tests.factories import (
    SensorFactory,
    MonitoringStationFactory,
    PollutantFactory,
    LocationFactory,
    DeviceStatusFactory
)

@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestDeviceSelectors:
    def test_get_aggregated_device_list_stations(self):
        station = MonitoringStationFactory(
            station_code="ST_TEST", 
            is_active=True,
            location=LocationFactory(full_address="Test Address")
        )
        pollutant = PollutantFactory(symbol="PM2.5")
        SensorFactory(monitoring_station=station, pollutant=pollutant, is_active=True)
        
        result = get_aggregated_device_list({"type": "station", "search": "ST_TEST"})
        assert len(result) >= 1
        assert any(r["station_code"] == "ST_TEST" for r in result)
        assert result[0]["type"] == "Stacja"
        assert "PM2.5" in result[0]["pollutants"]

    def test_get_aggregated_device_list_sensors(self):
        sensor = SensorFactory(
            serial_number="SN_TEST",
            sensor_type="Temp",
            is_active=True,
            monitoring_station=MonitoringStationFactory(station_code="ST_PARENT")
        )
        
        result = get_aggregated_device_list({"type": "sensor", "search": "SN_TEST"})
        assert len(result) >= 1
        assert any(r["serial_number"] == "SN_TEST" for r in result)
        assert result[0]["type"] == "Czujnik"
        assert result[0]["address"] == "ST_PARENT"

    def test_get_aggregated_device_list_filters(self):
        active_sensor = SensorFactory(is_active=True, serial_number="UNIQUE_ACTIVE_SN_XYZ")
        inactive_sensor = SensorFactory(is_active=False, serial_number="UNIQUE_INACTIVE_SN_XYZ")
        
        result_active = get_aggregated_device_list({"type": "sensor", "is_active": "true", "search": "UNIQUE_ACTIVE_SN_XYZ"})
        assert len(result_active) == 1
        assert result_active[0]["serial_number"] == "UNIQUE_ACTIVE_SN_XYZ"
        
        result_search = get_aggregated_device_list({"type": "sensor", "search": "UNIQUE_ACTIVE_SN_XYZ"})
        assert len(result_search) == 1
        assert result_search[0]["serial_number"] == "UNIQUE_ACTIVE_SN_XYZ"


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestSensorService:
    @patch("pollution_backend.services.sensors.broadcast_sensor_status")
    @patch("pollution_backend.services.sensors.publish_mqtt_command")
    def test_reset_sensor(self, mock_mqtt, mock_broadcast):
        sensor = SensorFactory(is_active=False)
        DeviceStatusFactory(sensor=sensor, uptime_seconds=5000)
        
        status = SensorService.reset_sensor(sensor)
        
        assert status.uptime_seconds == 0
        assert status.battery_percent == 100
        sensor.refresh_from_db()
        assert sensor.is_active is True
        
        mock_broadcast.assert_called_once()
        mock_mqtt.assert_called_once()
        assert SystemLog.objects.filter(event_type="DEVICE_RESET", sensor_id=sensor.id).exists()

    @patch("pollution_backend.services.sensors.broadcast_sensor_log")
    def test_log_sensor_action(self, mock_broadcast_log):
        sensor = SensorFactory()
        
        SensorService.log_sensor_action(
            sensor=sensor,
            action_type="TEST_ACTION",
            message="Test message",
            level="info"
        )
        
        assert SystemLog.objects.filter(event_type="TEST_ACTION", sensor_id=sensor.id).exists()
        mock_broadcast_log.assert_called_once()
