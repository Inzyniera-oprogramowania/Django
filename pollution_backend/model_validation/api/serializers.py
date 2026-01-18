from rest_framework import serializers

from pollution_backend.model_validation.models import ModelValidationRun, ValidationMetric, ValidationErrorLog


class ValidationRequestSerializer(serializers.Serializer):
    model_name = serializers.CharField(max_length=100, required=False)
    run_name = serializers.CharField(max_length=255, required=False)


class ValidationRunListSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source='forecast_area.name', read_only=True)

    class Meta:
        model = ModelValidationRun
        fields = [
            'id',
            'name',
            'model_name',
            'executed_at',
            'area_name',
            'data_start_time',
            'data_end_time'
        ]


class ValidationMetricSerializer(serializers.ModelSerializer):
    pollutant_name = serializers.CharField(source='pollutant.name', read_only=True)
    pollutant_symbol = serializers.CharField(source='pollutant.symbol', read_only=True)

    class Meta:
        model = ValidationMetric
        fields = [
            'metric_name',
            'metric_value',
            'pollutant_name',
            'pollutant_symbol'
        ]


class ValidationErrorLogSerializer(serializers.ModelSerializer):
    pollutant_symbol = serializers.CharField(source='pollutant.symbol', read_only=True)

    class Meta:
        model = ValidationErrorLog
        fields = [
            'time',
            'predicted_value',
            'actual_value',
            'error_diff',
            'pollutant_symbol'
        ]


class ValidationRunDetailSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source='forecast_area.name', read_only=True)
    metrics = ValidationMetricSerializer(many=True, read_only=True)
    error_logs = ValidationErrorLogSerializer(many=True, read_only=True)

    class Meta:
        model = ModelValidationRun
        fields = [
            'id',
            'name',
            'model_name',
            'executed_at',
            'area_name',
            'data_start_time',
            'data_end_time',
            'metrics',
            'error_logs'
        ]
