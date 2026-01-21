from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from pollution_backend.sensors.models import AnomalyLog
from pollution_backend.sensors.models import AnomalyRule
from pollution_backend.sensors.models import GlobalAnomalyConfig
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
    station_code = serializers.CharField(
        source="sensor.monitoring_station.station_code", read_only=True
    )
    pollutant_symbol = serializers.CharField(
        source="sensor.pollutant.symbol", read_only=True
    )
    pollutant_name = serializers.CharField(
        source="sensor.pollutant.name", read_only=True
    )
    sensor_serial_number = serializers.CharField(
        source="sensor.serial_number", read_only=True
    )

    class Meta:
        model = AnomalyLog
        fields = [
            "id",
            "description",
            "detected_at",
            "status",
            "severity",
            "sensor",
            "station_code",
            "pollutant_symbol",
            "pollutant_name",
            "sensor_serial_number",
        ]
        read_only_fields = ["id", "description", "detected_at", "sensor", "severity"]


class AnomalyRuleSerializer(serializers.ModelSerializer):
    pollutant_symbol = serializers.CharField(source="pollutant.symbol", read_only=True)
    pollutant_name = serializers.CharField(source="pollutant.name", read_only=True)

    class Meta:
        model = AnomalyRule
        fields = [
            "id",
            "pollutant",
            "pollutant_symbol",
            "pollutant_name",
            "is_enabled",
            "warning_threshold",
            "critical_threshold",
            "sudden_change_enabled",
            "sudden_change_percent",
            "sudden_change_minutes",
        ]
        read_only_fields = ["id", "pollutant", "pollutant_symbol", "pollutant_name"]


class GlobalAnomalyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalAnomalyConfig
        fields = ["id", "missing_data_timeout_minutes"]
        read_only_fields = ["id"]

