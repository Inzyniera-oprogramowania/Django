import pytest
from datetime import timedelta
from django.utils import timezone

from pollution_backend.tasks.realtime import check_anomaly
from pollution_backend.sensors.models import AnomalyLog
from pollution_backend.sensors.tests.factories import (
    SensorFactory,
    PollutantFactory,
    AnomalyRuleFactory,
)


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestCheckAnomalyTask:
    @pytest.fixture
    def pollutant(self):
        return PollutantFactory(symbol="PM10_ANOM")

    @pytest.fixture
    def sensor(self, pollutant):
        return SensorFactory(is_active=True, pollutant=pollutant)

    @pytest.fixture
    def anomaly_rule(self, pollutant):
        return AnomalyRuleFactory(
            pollutant=pollutant, is_enabled=True,
            warning_threshold=50.0, critical_threshold=100.0
        )

    @pytest.fixture
    def timestamp(self):
        return timezone.now().isoformat()

    def test_no_anomaly_when_value_below_threshold(self, sensor, anomaly_rule, timestamp):
        # Brak anomalii gdy wartość poniżej lub równa progowi
        for value in [30.0, 50.0]:  # poniżej i równo
            result = check_anomaly(sensor_id=sensor.id, value=value, timestamp=timestamp)
            assert result["is_anomaly"] is False

    def test_warning_anomaly_detected(self, sensor, anomaly_rule, timestamp):
        # Wykrywa anomalię warning (powyżej warning, poniżej critical)
        result = check_anomaly(sensor_id=sensor.id, value=75.0, timestamp=timestamp)
        assert result["is_anomaly"] is True
        assert "WARNING" in result["message"]
        anomaly = AnomalyLog.objects.get(id=result["anomaly_id"])
        assert anomaly.severity == "warning"
        assert anomaly.status == "pending"
        assert "75.00" in anomaly.description
        assert sensor.pollutant.symbol in anomaly.description

    def test_critical_anomaly_detected(self, sensor, anomaly_rule, timestamp):
        # Wykrywa anomalię critical (powyżej critical threshold)
        result = check_anomaly(sensor_id=sensor.id, value=150.0, timestamp=timestamp)
        assert result["is_anomaly"] is True
        assert "CRITICAL" in result["message"]
        anomaly = AnomalyLog.objects.get(id=result["anomaly_id"])
        assert anomaly.severity == "critical"

    def test_edge_cases_return_no_anomaly(self, timestamp):
        # Obsługa błędnych danych: nieistniejący sensor, brak reguły, wyłączona reguła
        # Nieistniejący sensor
        result = check_anomaly(sensor_id=99999, value=100.0, timestamp=timestamp)
        assert result["is_anomaly"] is False
        assert "not found" in result["message"]
        
        # Sensor bez reguły
        sensor_without_rule = SensorFactory(is_active=True)
        result = check_anomaly(sensor_id=sensor_without_rule.id, value=100.0, timestamp=timestamp)
        assert result["is_anomaly"] is False
        assert "No rule" in result["message"]

    def test_disabled_rule_no_anomaly(self, sensor, pollutant, timestamp):
        # Wyłączona reguła nie wykrywa anomalii
        AnomalyRuleFactory(pollutant=pollutant, is_enabled=False, warning_threshold=50.0, critical_threshold=100.0)
        result = check_anomaly(sensor_id=sensor.id, value=200.0, timestamp=timestamp)
        assert result["is_anomaly"] is False

    def test_anomaly_log_stores_correct_time(self, sensor, anomaly_rule):
        # Sprawdza poprawność czasu wykrycia
        specific_time = "2024-01-15T10:30:00+00:00"
        result = check_anomaly(sensor_id=sensor.id, value=75.0, timestamp=specific_time)
        anomaly = AnomalyLog.objects.get(id=result["anomaly_id"])
        assert anomaly.detected_at.year == 2024
        assert anomaly.detected_at.month == 1

    def test_multiple_anomalies_create_multiple_logs(self, sensor, anomaly_rule):
        # Wiele anomalii tworzy wiele wpisów
        initial_count = AnomalyLog.objects.filter(sensor=sensor).count()
        for i in range(3):
            timestamp = (timezone.now() + timedelta(minutes=i)).isoformat()
            check_anomaly(sensor_id=sensor.id, value=75.0 + i, timestamp=timestamp)
        assert AnomalyLog.objects.filter(sensor=sensor).count() == initial_count + 3


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestAnomalyRuleThresholds:
    @pytest.fixture
    def pollutant(self):
        return PollutantFactory(symbol="NO2_TEST")

    @pytest.fixture
    def sensor(self, pollutant):
        return SensorFactory(is_active=True, pollutant=pollutant)

    def test_custom_thresholds(self, sensor, pollutant):
        # Testuje niestandardowe progi (niski warning, wysoki critical)
        AnomalyRuleFactory(pollutant=pollutant, is_enabled=True, warning_threshold=25.0, critical_threshold=500.0)
        timestamp = timezone.now().isoformat()
        
        # Poniżej warning
        assert check_anomaly(sensor_id=sensor.id, value=20.0, timestamp=timestamp)["is_anomaly"] is False
        # Warning
        result_warn = check_anomaly(sensor_id=sensor.id, value=30.0, timestamp=timestamp)
        assert AnomalyLog.objects.get(id=result_warn["anomaly_id"]).severity == "warning"
        # Critical
        result_crit = check_anomaly(sensor_id=sensor.id, value=600.0, timestamp=timestamp)
        assert AnomalyLog.objects.get(id=result_crit["anomaly_id"]).severity == "critical"


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestAnomalyDetectionTimestamp:
    @pytest.fixture
    def sensor(self):
        pollutant = PollutantFactory(symbol="O3_TIME")
        AnomalyRuleFactory(pollutant=pollutant, is_enabled=True, warning_threshold=50.0, critical_threshold=100.0)
        return SensorFactory(is_active=True, pollutant=pollutant)

    @pytest.mark.parametrize("timestamp", [
        "2024-06-15T14:30:00+00:00",  # UTC
        "2024-06-15T14:30:00Z",        # Zulu
        "2024-06-15T14:30:00+02:00",   # Pozytywne przesunięcie
        "2024-06-15T14:30:00-05:00",   # Negatywne przesunięcie
    ])
    def test_handles_various_timestamp_formats(self, sensor, timestamp):
        # Obsługuje różne formaty timestampów
        result = check_anomaly(sensor_id=sensor.id, value=75.0, timestamp=timestamp)
        assert result["is_anomaly"] is True
        assert AnomalyLog.objects.get(id=result["anomaly_id"]).detected_at is not None
