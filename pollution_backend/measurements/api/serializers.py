from django.utils import timezone
from rest_framework import serializers
from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.users.models import ApiKey
from pollution_backend.sensors.models import Sensor

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
        model = SystemLog
        fields = "__all__"


SAFE_LIMITS = {
    "PM10": (-1, 2000),
    "PM2.5": (-1, 1500),
    "TEMP": (-50, 60),
    "HUMIDITY": (0, 100),
    "PRESSURE": (900, 1100),
}

class MeasurementImportSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField(required=True)
    value = serializers.FloatField(required=True)
    timestamp = serializers.DateTimeField(required=True) 
    unit = serializers.CharField(required=True, max_length=10)

    def validate_timestamp(self, value):
        if value > timezone.now() + timezone.timedelta(minutes=5):
            raise serializers.ValidationError("Data pomiaru nie może być z przyszłości.")
        return value

    def validate_sensor_id(self, value):
        if not Sensor.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Sensor o ID {value} nie istnieje.")
        return value

    def validate(self, data):
        sensor_id = data.get('sensor_id')
        value = data.get('value')
        unit = data.get('unit')

        try:
            sensor = Sensor.objects.select_related('pollutant', 'monitoring_station').get(id=sensor_id)
        except Sensor.DoesNotExist:
            raise serializers.ValidationError({"sensor_id": "Sensor nie istnieje."})

        request = self.context.get('request')
        if request and hasattr(request, 'auth') and isinstance(request.auth, ApiKey):
            api_key = request.auth
            if api_key.station and api_key.station.id != sensor.monitoring_station.id:
                 raise serializers.ValidationError({
                     "sensor_id": f"Twój klucz API jest przypisany do stacji {api_key.station.station_code}, a próbujesz wysłać dane do innej stacji."
                 })

        pollutant_symbol = sensor.pollutant.symbol
        
        if pollutant_symbol == "PM10" and unit not in ['µg/m3', 'ug/m3']:
             raise serializers.ValidationError({"unit": f"Nieprawidłowa jednostka dla {pollutant_symbol}. Oczekiwano µg/m3."})
        
        if pollutant_symbol == "TEMP" and unit not in ['C', 'Celsius']:
             raise serializers.ValidationError({"unit": "Temperatura musi być w Celsjuszach."})

        min_val, max_val = SAFE_LIMITS.get(pollutant_symbol, (-100, 1000))
        
        if not (min_val <= value <= max_val):
            raise serializers.ValidationError({
                "value": f"Wartość {value} dla {pollutant_symbol} jest poza fizycznym zakresem ({min_val} - {max_val})."
            })

        return data