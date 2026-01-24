from rest_framework import serializers

from pollution_backend.measurements.models import Measurement
from pollution_backend.users.models import ApiKey
from pollution_backend.sensors.models import Sensor
from pollution_backend.measurements.models import SystemLog

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


class MeasurementImportSerializer(serializers.Serializer):
    sensor_id = serializers.IntegerField(required=True)
    value = serializers.FloatField(required=True)
    timestamp = serializers.DateTimeField(required=True) 
    unit = serializers.CharField(required=True, max_length=10)

    def validate_sensor_id(self, value):
        if not Sensor.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Sensor o ID {value} nie istnieje.")
        return value

    def validate_value(self, value):
        if value < -100 or value > 1000:
            raise serializers.ValidationError("Wartość pomiaru poza dopuszczalnym zakresem fizycznym (-100 do 1000).")
        return value

    def validate(self, data):
        try:
            sensor = Sensor.objects.get(id=data['sensor_id'])
            
            request = self.context.get('request')
            if request and hasattr(request, 'auth') and isinstance(request.auth, ApiKey):
                api_key = request.auth
                if api_key.station and api_key.station != sensor.monitoring_station:
                     raise serializers.ValidationError({"sensor_id": f"Klucz API jest ograniczony do stacji {api_key.station.station_code}. Nie masz uprawnień do tego sensora."})

            if sensor.pollutant.symbol == "PM10" and data['unit'] not in ['µg/m3', 'ug/m3']:
                 raise serializers.ValidationError({"unit": "Nieprawidłowa jednostka dla PM10. Oczekiwano µg/m3."})
        except Sensor.DoesNotExist:
            pass
            
        return data