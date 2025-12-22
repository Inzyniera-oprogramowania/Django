from rest_framework import serializers


class SensorSerializer(serializers.Serializer):
    """Definicja wyglądu obiektu Sensor dla Frontendu"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    location_lat = serializers.FloatField()
    location_lon = serializers.FloatField()
    status = serializers.CharField()


class MeasurementSerializer(serializers.Serializer):
    """Definicja pojedynczego punktu pomiarowego (np. na wykres)"""

    timestamp = serializers.DateTimeField()
    pm25 = serializers.FloatField()
    pm10 = serializers.FloatField()
    temperature = serializers.FloatField()
    humidity = serializers.FloatField()
