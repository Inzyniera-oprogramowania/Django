import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone
from pollution_backend.services.stations import StationService
from pollution_backend.services.measurements import MeasurementImportService
from pollution_backend.services.statistics import get_descriptive_stats, DescriptiveStats
from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.sensors.tests.factories import (
    SensorFactory,
    MonitoringStationFactory,
    PollutantFactory,
)
from pollution_backend.users.tests.factories import UserFactory

@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestStationService:
    @patch("pollution_backend.services.stations.requests.get")
    def test_create_station_with_mocked_geocode(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"lat": "51.1079", "lon": "17.0385", "display_name": "Wroclaw, Poland"}]
        mock_get.return_value = mock_response

        validated_data = {
            "address": "Wroclaw",
            "station_code": "ST_WRO",
            "owner": "City Council"
        }
        station, geo_data = StationService.create_station(validated_data)

        assert station.station_code == "ST_WRO"
        assert station.location.geom.x == 17.0385
        assert station.location.geom.y == 51.1079
        assert station.location.full_address == "Wroclaw, Poland"

    @patch("pollution_backend.services.stations.requests.get")
    def test_create_station_fallback_geocode(self, mock_get):
        mock_get.side_effect = Exception("API Error")

        validated_data = {
            "address": "Unknown Place",
            "station_code": "ST_UNK",
        }
        station, geo_data = StationService.create_station(validated_data)

        assert station.location.geom.y == 52.2297

@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestMeasurementImportService:
    def test_batch_import_success(self):
        user = UserFactory()
        sensor = SensorFactory(is_active=True)
        items = [
            {
                "sensor_id": sensor.id,
                "value": 15.5,
                "unit": "µg/m³",
                "timestamp": timezone.now()
            },
            {
                "sensor_id": sensor.id,
                "value": 20.0,
                "unit": "µg/m³",
                "timestamp": timezone.now() - timedelta(minutes=5)
            }
        ]

        count_before = Measurement.objects.count()
        MeasurementImportService.process_batch(items, user.id, None)

        assert Measurement.objects.count() == count_before + 2
        assert SystemLog.objects.filter(event_type="import_success").exists()
        
    def test_batch_import_partial_failure(self):
        user = UserFactory()
        sensor = SensorFactory(is_active=True)
        items = [
            {
                "sensor_id": sensor.id,
                "value": 15.5,
                "unit": "µg/m³",
                "timestamp": timezone.now()
            },
            {
                "sensor_id": 9999,
                "value": 20.0,
                "unit": "µg/m³",
                "timestamp": timezone.now()
            }
        ]

        count_before = Measurement.objects.count()
        MeasurementImportService.process_batch(items, user.id, None)

        assert Measurement.objects.count() == count_before + 1
        assert SystemLog.objects.filter(event_type="import_success").exists()

