"""
Serializers for analysis API endpoints.
"""
from rest_framework import serializers


class AnalysisRequestSerializer(serializers.Serializer):
    """Request serializer for running analysis."""
    
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
    
    sensor_id = serializers.IntegerField(
        help_text="ID czujnika do analizy"
    )
    analysis_type = serializers.ChoiceField(
        choices=ANALYSIS_TYPES,
        help_text="Typ analizy do wykonania"
    )
    date_from = serializers.DateTimeField(
        help_text="Data początkowa zakresu"
    )
    date_to = serializers.DateTimeField(
        help_text="Data końcowa zakresu"
    )
    aggregation = serializers.ChoiceField(
        choices=AGGREGATION_CHOICES,
        default="hour",
        required=False,
        help_text="Agregacja czasowa dla analizy trendów"
    )
    # For period comparison
    period2_from = serializers.DateTimeField(
        required=False,
        help_text="Data początkowa drugiego okresu (dla porównania)"
    )
    period2_to = serializers.DateTimeField(
        required=False,
        help_text="Data końcowa drugiego okresu (dla porównania)"
    )

    def validate(self, data):
        if data["analysis_type"] == "comparison":
            if not data.get("period2_from") or not data.get("period2_to"):
                raise serializers.ValidationError(
                    "Porównanie okresów wymaga period2_from i period2_to"
                )
        return data


class DescriptiveStatsSerializer(serializers.Serializer):
    """Serializer for descriptive statistics response."""
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
    """Serializer for time-series data points."""
    time = serializers.CharField()
    value = serializers.FloatField()


class TrendAnalysisSerializer(serializers.Serializer):
    """Serializer for trend analysis response."""
    trend_direction = serializers.CharField()
    percent_change = serializers.FloatField()
    slope = serializers.FloatField()
    start_avg = serializers.FloatField()
    end_avg = serializers.FloatField()
    data_points = DataPointSerializer(many=True)


class PeriodComparisonSerializer(serializers.Serializer):
    """Serializer for period comparison response."""
    period1_avg = serializers.FloatField()
    period2_avg = serializers.FloatField()
    absolute_diff = serializers.FloatField()
    percent_diff = serializers.FloatField()
    period1_max = serializers.FloatField()
    period2_max = serializers.FloatField()
    better_period = serializers.CharField()


class WorstDaySerializer(serializers.Serializer):
    """Serializer for worst day data."""
    date = serializers.CharField()
    max_value = serializers.FloatField()
    avg_value = serializers.FloatField()


class HourlyDistributionSerializer(serializers.Serializer):
    """Serializer for hourly distribution data."""
    hour = serializers.IntegerField()
    count = serializers.IntegerField()


class NormExceedanceSerializer(serializers.Serializer):
    """Serializer for norm exceedance analysis response."""
    total_measurements = serializers.IntegerField()
    exceedances_count = serializers.IntegerField()
    exceedance_percent = serializers.FloatField()
    norm_value = serializers.FloatField()
    norm_type = serializers.CharField()
    worst_days = WorstDaySerializer(many=True)
    hourly_distribution = HourlyDistributionSerializer(many=True)


class AnalysisResponseSerializer(serializers.Serializer):
    """Generic response serializer wrapping analysis results."""
    analysis_type = serializers.CharField()
    sensor_id = serializers.IntegerField()
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    sensor_info = serializers.DictField(required=False)
    results = serializers.DictField()


class ReportGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating reports."""
    title = serializers.CharField(max_length=255)
    sensor_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Lista ID czujników do raportu"
    )
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
