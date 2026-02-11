import uuid
import pytest
from datetime import timedelta
from django.utils import timezone

from pollution_backend.analysis.strategies import AnalysisStrategy
from pollution_backend.services.statistics import (
    get_descriptive_stats,
    get_trend_analysis,
    get_period_comparison,
    get_norm_exceedance_analysis,
    DescriptiveStats,
    TrendAnalysis,
    PeriodComparison,
    NormExceedance,
)
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.tests.factories import (
    SensorFactory,
    PollutantFactory,
)


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestAnalysisStrategy:
    @pytest.fixture
    def sensor(self):
        return SensorFactory(is_active=True)

    @pytest.fixture
    def measurements(self, sensor):
        base_time = timezone.now()
        for i, v in enumerate([10, 20, 30, 40, 50, 60, 70, 80, 90, 100]):
            Measurement.objects.create(sensor_id=sensor.id, value=v, unit="µg/m³", time=base_time - timedelta(hours=i))

    @pytest.mark.parametrize("analysis_type,expected_class", [
        ("descriptive", DescriptiveStats),
        ("trend", TrendAnalysis),
    ])
    def test_run_analysis_returns_correct_type(self, sensor, measurements, analysis_type, expected_class):
        # Sprawdza że run() zwraca poprawny typ dla różnych analiz
        data = {
            "sensor_id": sensor.id,
            "date_from": timezone.now() - timedelta(days=1),
            "date_to": timezone.now() + timedelta(days=1),
            "aggregation": "hour",
        }
        result, serializer_cls = AnalysisStrategy.run(analysis_type, data)
        assert result is not None
        assert isinstance(result, expected_class)

    def test_run_comparison_analysis(self, sensor):
        # Sprawdza porównanie okresów
        base_time = timezone.now()
        for i in range(5):
            Measurement.objects.create(sensor_id=sensor.id, value=20 + i, unit="µg/m³", time=base_time - timedelta(days=10, hours=i))
            Measurement.objects.create(sensor_id=sensor.id, value=40 + i, unit="µg/m³", time=base_time - timedelta(hours=i))
        data = {
            "sensor_id": sensor.id,
            "date_from": base_time - timedelta(days=11),
            "date_to": base_time - timedelta(days=9),
            "period2_from": base_time - timedelta(days=1),
            "period2_to": base_time + timedelta(days=1),
        }
        result, _ = AnalysisStrategy.run("comparison", data)
        assert isinstance(result, PeriodComparison)
        assert result.period1_avg < result.period2_avg

    def test_run_exceedance_analysis(self, sensor):
        # Sprawdza analizę przekroczeń norm
        QualityNorm.objects.create(pollutant=sensor.pollutant, threshold_value=50, unit="µg/m³", norm_type="daily")
        base_time = timezone.now()
        for i, v in enumerate([30, 40, 60, 70, 80]):
            Measurement.objects.create(sensor_id=sensor.id, value=v, unit="µg/m³", time=base_time - timedelta(hours=i))
        data = {"sensor_id": sensor.id, "date_from": base_time - timedelta(days=1), "date_to": base_time + timedelta(days=1)}
        result, _ = AnalysisStrategy.run("exceedance", data)
        assert isinstance(result, NormExceedance)
        assert result.exceedances_count >= 3

    def test_run_unknown_type_raises_error(self, sensor):
        # Nieznany typ analizy rzuca ValueError
        with pytest.raises(ValueError, match="Unknown analysis type"):
            AnalysisStrategy.run("unknown_type", {"sensor_id": sensor.id, "date_from": timezone.now(), "date_to": timezone.now()})

    def test_serialize_result(self, sensor, measurements):
        # Serializacja wyniku zwraca słownik
        data = {"sensor_id": sensor.id, "date_from": timezone.now() - timedelta(days=1), "date_to": timezone.now() + timedelta(days=1)}
        result, serializer_cls = AnalysisStrategy.run("descriptive", data)
        serialized = AnalysisStrategy.serialize_result(result, serializer_cls)
        assert isinstance(serialized, dict)
        assert "count" in serialized


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestStatisticsFunctions:
    @pytest.fixture
    def sensor(self):
        return SensorFactory()

    def test_get_descriptive_stats(self, sensor):
        # Oblicza statystyki opisowe
        now = timezone.now()
        values = [10, 20, 30, 40, 50]
        for i, v in enumerate(values):
            Measurement.objects.create(sensor_id=sensor.id, value=v, unit="µg/m³", time=now - timedelta(hours=i))
        stats = get_descriptive_stats(sensor_id=sensor.id, date_from=now - timedelta(days=1), date_to=now + timedelta(days=1))
        assert stats is not None
        assert stats.count >= 5
        assert stats.min_value <= 10
        assert stats.max_value >= 50
        assert stats.percentile_25 is not None

    def test_get_trend_analysis(self, sensor):
        # Analizuje trendy
        now = timezone.now()
        for i in range(10):
            Measurement.objects.create(sensor_id=sensor.id, value=10 + i * 10, unit="µg/m³", time=now - timedelta(hours=9-i))
        trend = get_trend_analysis(sensor_id=sensor.id, date_from=now - timedelta(days=1), date_to=now + timedelta(days=1), aggregation="hour")
        assert trend is not None
        assert len(trend.data_points) > 0

    def test_get_period_comparison(self, sensor):
        # Porównuje dwa okresy
        now = timezone.now()
        for i in range(5):
            Measurement.objects.create(sensor_id=sensor.id, value=20, unit="µg/m³", time=now - timedelta(days=10, hours=i))
            Measurement.objects.create(sensor_id=sensor.id, value=40, unit="µg/m³", time=now - timedelta(hours=i))
        comparison = get_period_comparison(
            sensor_id=sensor.id,
            period1_from=now - timedelta(days=11), period1_to=now - timedelta(days=9),
            period2_from=now - timedelta(days=1), period2_to=now + timedelta(days=1)
        )
        assert comparison is not None
        assert comparison.period1_avg <= comparison.period2_avg

    def test_get_norm_exceedance_analysis(self, sensor):
        # Analizuje przekroczenia norm
        pollutant = sensor.pollutant
        QualityNorm.objects.get_or_create(pollutant=pollutant, norm_type="daily", defaults={"threshold_value": 50, "unit": "µg/m³"})
        now = timezone.now()
        for i, v in enumerate([30, 40, 60, 70, 80]):
            Measurement.objects.create(sensor_id=sensor.id, value=v, unit="µg/m³", time=now - timedelta(hours=i))
        result = get_norm_exceedance_analysis(sensor_id=sensor.id, date_from=now - timedelta(days=1), date_to=now + timedelta(days=1))
        assert result is not None
        assert result.exceedances_count >= 3

    def test_functions_return_none_for_no_data(self, sensor):
        # Funkcje zwracają None gdy brak danych
        now = timezone.now()
        assert get_descriptive_stats(sensor_id=sensor.id, date_from=now, date_to=now) is None
        assert get_trend_analysis(sensor_id=sensor.id, date_from=now, date_to=now, aggregation="hour") is None
        assert get_norm_exceedance_analysis(sensor_id=99999, date_from=now, date_to=now) is None
