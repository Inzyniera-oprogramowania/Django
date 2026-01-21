from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from pollution_backend.sensors.models import AnomalyLog
from pollution_backend.sensors.models import Location
from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.sensors.models import Pollutant
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.sensors.models import Sensor


class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = "__all__"


class PollutantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pollutant
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"


# Monitoring station z geom dla mapy
class MonitoringStationGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = MonitoringStation
        geo_field = "location"
        fields = ["id", "station_code", "owner", "is_active"]


class MonitoringStationFlatSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(source="location.geom.y", read_only=True)
    lon = serializers.FloatField(source="location.geom.x", read_only=True)
    address = serializers.CharField(source="location.full_address", read_only=True)

    class Meta:
        model = MonitoringStation
        fields = ["id", "station_code", "owner", "is_active", "lat", "lon", "address"]



# Dokladny serializer monitoring station z sensorami i lokalizacja
class MonitoringStationDetailSerializer(serializers.ModelSerializer):
    sensors = SensorSerializer(many=True, read_only=True, source="sensor_set")

    address = serializers.CharField(source="location.full_address", read_only=True)
    alt = serializers.FloatField(source="location.altitude", read_only=True)
    lat = serializers.FloatField(source="location.geom.y", read_only=True)
    lon = serializers.FloatField(source="location.geom.x", read_only=True)

    class Meta:
        model = MonitoringStation
        fields = [
            "id",
            "station_code",
            "owner",
            "launch_date",
            "decommission_date",
            "is_active",
            "sensors",
            "address",
            "alt",
            "lat",
            "lon",
        ]


class QualityNormSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityNorm
        fields = "__all__"


class AnomalyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyLog
        fields = "__all__"


class DeviceSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    pollutants = serializers.ListField(child=serializers.CharField(), required=False)
    address = serializers.CharField()
    lastLogTime = serializers.CharField()
    is_active = serializers.BooleanField()


class StationCreateSerializer(serializers.Serializer):
    station_code = serializers.CharField(max_length=50)
    address = serializers.CharField(max_length=255)
    owner = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate_station_code(self, value):
        if MonitoringStation.objects.filter(station_code=value).exists():
            raise serializers.ValidationError("Stacja o tym kodzie już istnieje.")
        return value


class SensorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = [
            'serial_number', 'sensor_type', 'manufacturer', 'model',
            'monitoring_station', 'pollutant', 'calibration_date',
            'measurement_range_max', 'send_interval_seconds'
        ]
    
    def validate_serial_number(self, value):
        if value and Sensor.objects.filter(serial_number=value).exists():
            raise serializers.ValidationError("Czujnik o tym numerze seryjnym już istnieje.")
        return value


