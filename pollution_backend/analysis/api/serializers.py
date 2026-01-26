from rest_framework import serializers
from pollution_backend.sensors.models import Sensor

class AnalysisRequestSerializer(serializers.Serializer):
    ANALYSIS_TYPES = [
        ("descriptive", "Statystyki opisowe"),
        ("trend", "Analiza trendów"),
        ("comparison", "Porównanie okresów"),
        ("exceedance", "Analiza przekroczeń norm"),
    ]
    
    AGGREGATION_CHOICES = [
        ("hour", "Godzinowa"),
        ("day", "Dzienna"),
    ]
    
    sensor_id = serializers.IntegerField()
    analysis_type = serializers.ChoiceField(choices=ANALYSIS_TYPES)
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    aggregation = serializers.ChoiceField(
        choices=AGGREGATION_CHOICES,
        default="hour",
        required=False
    )
    period2_from = serializers.DateTimeField(required=False)
    period2_to = serializers.DateTimeField(required=False)

    def validate(self, data):
        if data["analysis_type"] == "comparison":
            if not data.get("period2_from") or not data.get("period2_to"):
                raise serializers.ValidationError(
                    "Porównanie okresów wymaga period2_from i period2_to"
                )
        return data

class QuickStatsRequestSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField(required=True)
    days = serializers.IntegerField(required=False, default=7, min_value=1, max_value=365)

class SensorInfoSerializer(serializers.ModelSerializer):
    pollutant = serializers.CharField(source='pollutant.symbol', read_only=True)
    pollutant_name = serializers.CharField(source='pollutant.name', read_only=True)
    station_code = serializers.CharField(source='monitoring_station.station_code', read_only=True)
    location = serializers.CharField(source='monitoring_station.location.full_address', read_only=True)
    
    class Meta:
        model = Sensor
        fields = ['id', 'sensor_type', 'serial_number', 'pollutant', 'pollutant_name', 'station_code', 'location']

class DescriptiveStatsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    mean = serializers.FloatField()
    min_value = serializers.FloatField()
    max_value = serializers.FloatField()
    std_dev = serializers.FloatField()
    median = serializers.FloatField()
    percentile_25 = serializers.FloatField()
    percentile_75 = serializers.FloatField()
    percentile_95 = serializers.FloatField()
    unit = serializers.CharField()

class DataPointSerializer(serializers.Serializer):
    time = serializers.CharField()
    value = serializers.FloatField()

class TrendAnalysisSerializer(serializers.Serializer):
    trend_direction = serializers.CharField()
    percent_change = serializers.FloatField()
    slope = serializers.FloatField()
    start_avg = serializers.FloatField()
    end_avg = serializers.FloatField()
    data_points = DataPointSerializer(many=True)

class PeriodComparisonSerializer(serializers.Serializer):
    period1_avg = serializers.FloatField()
    period2_avg = serializers.FloatField()
    absolute_diff = serializers.FloatField()
    percent_diff = serializers.FloatField()
    period1_max = serializers.FloatField()
    period2_max = serializers.FloatField()
    better_period = serializers.CharField()

class WorstDaySerializer(serializers.Serializer):
    date = serializers.CharField()
    max_value = serializers.FloatField()
    avg_value = serializers.FloatField()

class HourlyDistributionSerializer(serializers.Serializer):
    hour = serializers.IntegerField()
    count = serializers.IntegerField()

class NormExceedanceSerializer(serializers.Serializer):
    total_measurements = serializers.IntegerField()
    exceedances_count = serializers.IntegerField()
    exceedance_percent = serializers.FloatField()
    norm_value = serializers.FloatField()
    norm_type = serializers.CharField()
    worst_days = WorstDaySerializer(many=True)
    hourly_distribution = HourlyDistributionSerializer(many=True)

class AnalysisResponseSerializer(serializers.Serializer):
    analysis_type = serializers.CharField()
    sensor_id = serializers.IntegerField()
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    sensor_info = serializers.DictField(required=False)
    results = serializers.DictField()

class ReportGenerateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    sensor_ids = serializers.ListField(child=serializers.IntegerField())
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    include_stats = serializers.BooleanField(default=True)
    include_trends = serializers.BooleanField(default=True)
    include_exceedances = serializers.BooleanField(default=True)
    include_charts = serializers.BooleanField(default=True)
    output_format = serializers.ChoiceField(
        choices=[("pdf", "PDF"), ("html", "HTML")],
        default="pdf"
    )