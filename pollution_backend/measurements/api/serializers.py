from rest_framework import serializers

from pollution_backend.measurements.models import Measurement


class MeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measurement
        fields = "__all__"


class AggregatedMeasurementSerializer(serializers.Serializer):
    bucket = serializers.DateTimeField()
    avg_value = serializers.FloatField()
    min_value = serializers.FloatField()
    max_value = serializers.FloatField()


class SystemLogSerializer(serializers.ModelSerializer):
    class Meta:
        from pollution_backend.measurements.models import SystemLog
        model = SystemLog
        fields = "__all__"

