import os
import pytest
from datetime import date, timedelta
from django.utils import timezone

from pollution_backend.services.analysis_report import AnalysisReportGenerator
from pollution_backend.reports.models import Report
from pollution_backend.sensors.tests.factories import SensorFactory
from pollution_backend.users.tests.factories import UserFactory, AdvancedUserFactory


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestAnalysisReportGenerator:
    @pytest.fixture
    def user(self):
        return UserFactory()

    @pytest.fixture
    def advanced_user(self):
        return AdvancedUserFactory()

    @pytest.fixture
    def sensor(self):
        return SensorFactory()

    @pytest.fixture
    def descriptive_data(self, sensor):
        return {
            "title": "Raport statystyk opisowych",
            "analysis_type": "descriptive",
            "sensor_id": sensor.id,
            "date_from": date.today() - timedelta(days=7),
            "date_to": date.today(),
            "results": {
                "count": 168, "mean": 45.5, "median": 42.0,
                "min_value": 10.0, "max_value": 98.0, "std_dev": 15.3, "unit": "µg/m³",
            }
        }

    @pytest.mark.parametrize("analysis_type", ["descriptive", "trend", "comparison", "exceedance"])
    def test_generate_report_returns_valid_pdf(self, user, sensor, analysis_type):
        # Generuje poprawny PDF dla każdego typu analizy
        data = {
            "title": "Test Report",
            "analysis_type": analysis_type,
            "sensor_id": sensor.id,
            "date_from": date.today() - timedelta(days=7),
            "date_to": date.today(),
            "results": {"count": 10, "mean": 30}
        }
        generator = AnalysisReportGenerator(data, user)
        pdf_content, filename = generator.generate()
        assert pdf_content.startswith(b"%PDF")
        assert analysis_type in filename
        assert len(pdf_content) > 1000

    def test_generate_report_with_datetime_dates(self, user, sensor):
        # Obsługuje datetime zamiast date
        data = {
            "title": "Test Report",
            "analysis_type": "descriptive",
            "sensor_id": sensor.id,
            "date_from": timezone.now() - timedelta(days=7),
            "date_to": timezone.now(),
            "results": {"count": 10, "mean": 30, "median": 28, "min_value": 10, "max_value": 50, "std_dev": 5, "unit": "µg/m³"},
        }
        generator = AnalysisReportGenerator(data, user)
        pdf_content, filename = generator.generate()
        assert pdf_content.startswith(b"%PDF")

    def test_save_to_report_creates_complete_record(self, advanced_user, descriptive_data, settings):
        # Tworzy kompletny rekord w bazie z plikiem i powiązaniami
        user = advanced_user.user
        generator = AnalysisReportGenerator(descriptive_data, user)
        report = generator.save_to_report()
        
        assert report is not None
        assert Report.objects.filter(id=report.id).exists()
        assert report.title == descriptive_data["title"]
        assert report.advanced_user == advanced_user
        assert report.parameters["analysis_type"] == "descriptive"
        assert report.results["count"] == 168
        
        file_path = os.path.join(settings.MEDIA_ROOT, 'reports', os.path.basename(report.file.name))
        assert os.path.exists(file_path)

    def test_save_multiple_reports(self, advanced_user, sensor, settings):
        # Zapisuje wiele raportów jako osobne wpisy
        user = advanced_user.user
        initial_count = Report.objects.count()
        
        for analysis_type in ["descriptive", "trend"]:
            data = {"title": f"Report {analysis_type}", "analysis_type": analysis_type, 
                    "sensor_id": sensor.id, "date_from": date.today(), "date_to": date.today(), "results": {}}
            gen = AnalysisReportGenerator(data, user)
            gen.save_to_report()
        
        assert Report.objects.count() == initial_count + 2


@pytest.mark.django_db(databases=['default', 'timeseries'])
class TestAnalysisReportGeneratorFormatting:
    @pytest.fixture
    def user(self):
        return UserFactory()

    @pytest.mark.parametrize("analysis_type,method_name", [
        ("descriptive", "_descriptive"),
        ("trend", "_trend"),
        ("comparison", "_comparison"),
        ("exceedance", "_exceedance"),
    ])
    def test_section_formatting_returns_elements(self, user, analysis_type, method_name):
        # Sprawdza że formatowanie sekcji zwraca elementy
        data = {"title": "Test", "analysis_type": analysis_type, "sensor_id": 1,
                "date_from": date.today(), "date_to": date.today(),
                "results": {"count": 100, "mean": 50.0, "trend_direction": "increasing",
                           "period1_avg": 30, "period2_avg": 45, "exceedances_count": 10}}
        generator = AnalysisReportGenerator(data, user)
        method = getattr(generator, method_name)
        elements = method(data["results"])
        assert len(elements) > 0

    def test_analysis_type_labels_exist(self, user):
        # Sprawdza istnienie etykiet dla typów analizy
        data = {"title": "Test", "analysis_type": "descriptive", "results": {}}
        generator = AnalysisReportGenerator(data, user)
        for analysis_type in ["descriptive", "trend", "comparison", "exceedance"]:
            assert analysis_type in generator.ANALYSIS_TYPE_LABELS
