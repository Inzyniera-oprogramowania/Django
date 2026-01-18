from rest_framework import serializers

from pollution_backend.forecasts.models import Forecast, ForecastPollutant


class ForecastRequestSerializer(serializers.Serializer):
    h3_index = serializers.CharField(max_length=15, min_length=15)
    pollutants = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False
    )
    model_name = serializers.CharField(max_length=100, required=False)


class ForecastListSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source='forecast_area.name', read_only=True)

    class Meta:
        model = Forecast
        fields = ['id', 'forecast_date', 'created_at', 'area_name']


class ForecastPollutantSerializer(serializers.ModelSerializer):
    pollutant_name = serializers.CharField(source='pollutant.name', read_only=True)
    pollutant_symbol = serializers.CharField(source='pollutant.symbol', read_only=True)

    class Meta:
        model = ForecastPollutant
        fields = [
            'forecast_timestamp',
            'predicted_value',
            'uncertainty',
            'pollutant_name',
            'pollutant_symbol'
        ]


class ForecastDetailSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source='forecast_area.name', read_only=True)
    pollutant_data = ForecastPollutantSerializer(source='forecastpollutant_set', many=True, read_only=True)

    class Meta:
        model = Forecast
        fields = [
            'id',
            'forecast_date',
            'created_at',
            'time_horizon',
            'area_name',
            'pollutant_data'
        ]
