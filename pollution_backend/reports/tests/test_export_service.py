import pytest
import json
import csv
import io
import datetime
import random
from django.utils import timezone
from pollution_backend.services.reports import ExportService
from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.tests.factories import MonitoringStationFactory, SensorFactory
from pollution_backend.users.tests.factories import UserFactory
from django.db import transaction

@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestExportService:
    
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.user = UserFactory()
        suffix = random.randint(10000, 99999)
        self.station = MonitoringStationFactory(station_code=f"ST_EXP_{suffix}")
        self.sensor = SensorFactory(
            monitoring_station=self.station, 
            sensor_type="PM10",
            serial_number=f"SN_EXP_{suffix}"
        )
        
        now = timezone.now()
        
        Measurement.objects.create(sensor_id=self.sensor.id, value=10, unit="PM10", time=now - datetime.timedelta(hours=1))
        Measurement.objects.create(sensor_id=self.sensor.id, value=15, unit="PM10", time=now - datetime.timedelta(hours=2))
        Measurement.objects.create(sensor_id=self.sensor.id, value=20, unit="PM10", time=now - datetime.timedelta(hours=3))
        
        Measurement.objects.create(sensor_id=self.sensor.id, value=50, unit="PM10", time=now - datetime.timedelta(days=1))

    def test_generate_csv_success(self):
        today = timezone.now().date()
        data = {
            "date_from": today - datetime.timedelta(days=1),
            "date_to": today + datetime.timedelta(days=1),
            "station_ids": [self.station.id],
            "file_format": "csv"
        }
        
        service = ExportService(data, self.user)
        result = service.generate_file()
        
        assert result is not None
        content, content_type, filename, checksum, total, preview = result
        
        assert content_type == "text/csv"
        assert total == 4
        assert "PM10" in str(content)

    def test_generate_json_success(self):
        today = timezone.now().date()
        data = {
            "date_from": today - datetime.timedelta(days=1),
            "date_to": today + datetime.timedelta(days=1),
            "station_ids": [self.station.id],
            "file_format": "json"
        }
        
        service = ExportService(data, self.user)
        result = service.generate_file()
        
        assert result is not None
        content, content_type, filename, checksum, total, preview = result
        
        assert content_type == "application/json"
        parsed = json.loads(content)
        assert len(parsed) == 4

    def test_generate_no_data(self):
        today = timezone.now().date()
        future_date = today + datetime.timedelta(days=365)
        
        data = {
            "date_from": future_date,
            "date_to": future_date,
            "station_ids": [self.station.id],
            "file_format": "csv"
        }
        
        service = ExportService(data, self.user)
        result = service.generate_file()
        
        assert result is None

    def test_generate_xml(self):
        today = timezone.now().date()
        data = {
            "date_from": today - datetime.timedelta(days=1),
            "date_to": today + datetime.timedelta(days=1),
            "station_ids": [self.station.id],
            "file_format": "xml"
        }
        
        service = ExportService(data, self.user)
        result = service.generate_file()
        
        assert result is not None
        content, content_type, filename, checksum, total, preview = result
        assert content_type == "application/xml"
        assert "<measurements>" in str(content)