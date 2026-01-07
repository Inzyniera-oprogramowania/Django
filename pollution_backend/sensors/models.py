from django.contrib.gis.db import models as geomodels
from django.db import models


class Pollutant(models.Model):
    name = models.CharField(unique=True, max_length=100)
    symbol = models.CharField(unique=True, max_length=20)
    description = models.TextField(blank=True, null=True)  # noqa: DJ001

    class Meta:
        db_table = "pollutant"
        managed = False

    def __str__(self):
        return self.symbol


class Location(models.Model):
    geom = geomodels.PointField(srid=4326)
    altitude = models.FloatField(blank=True, null=True)
    full_address = models.CharField(max_length=255, blank=True, null=True)  # noqa: DJ001
    h3_index = models.CharField(max_length=15, blank=True, null=True)  # noqa: DJ001
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "location"
        managed = False

    def __str__(self):
        return self.full_address or f"Location {self.id}"


class MonitoringStation(models.Model):
    station_code = models.CharField(unique=True, max_length=50)
    owner = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001
    launch_date = models.DateField(blank=True, null=True)
    decommission_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.RESTRICT,
        db_column="locationid",
    )

    class Meta:
        db_table = "monitoringstation"
        managed = False

    def __str__(self):
        return self.station_code


class Sensor(models.Model):
    sensor_type = models.CharField(max_length=50)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001
    model = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001
    serial_number = models.CharField(unique=True, max_length=100, blank=True, null=True)
    calibration_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    monitoring_station = models.ForeignKey(
        MonitoringStation,
        on_delete=models.CASCADE,
        db_column="monitoringstationid",
    )
    pollutant = models.ForeignKey(
        Pollutant,
        on_delete=models.RESTRICT,
        db_column="pollutantid",
    )

    class Meta:
        db_table = "sensor"
        managed = False

    def __str__(self):
        return f"{self.sensor_type} ({self.serial_number or 'No Serial'})"


class QualityNorm(models.Model):
    threshold_value = models.FloatField()
    unit = models.CharField(max_length=20)
    norm_type = models.CharField(max_length=50)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    pollutant = models.ForeignKey(
        Pollutant,
        on_delete=models.CASCADE,
        db_column="pollutantid",
    )

    class Meta:
        db_table = "qualitynorm"
        managed = False

    def __str__(self):
        return f"{self.pollutant.symbol} - {self.norm_type} ({self.threshold_value})"


class AnomalyLog(models.Model):
    description = models.CharField(max_length=255)
    detected_at = models.DateTimeField()
    status = models.CharField(max_length=50)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, db_column="sensorid")

    class Meta:
        db_table = "anomalylog"
        managed = False

    def __str__(self):
        return f"Anomaly: {self.description[:30]}..."
