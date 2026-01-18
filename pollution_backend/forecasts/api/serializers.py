from rest_framework import serializers


class ForecastRequestSerializer(serializers.Serializer):
    h3_index = serializers.CharField(max_length=15, min_length=15)
    pollutants = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False
    )
    model_name = serializers.CharField(max_length=100, required=False)
