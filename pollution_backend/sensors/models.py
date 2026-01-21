import sys

from django.contrib.gis.db import models as geomodels
from django.db import models

TESTING = "pytest" in sys.modules


class Pollutant(models.Model):
    name = models.CharField(unique=True, max_length=100)
    symbol = models.CharField(unique=True, max_length=20)
    description = models.TextField(blank=True, null=True)  # noqa: DJ001

    class Meta:
        db_table = "pollutant"
        managed = TESTING

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
        managed = TESTING

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
        managed = TESTING

    def __str__(self):
        return self.station_code


class Sensor(models.Model):
    sensor_type = models.CharField(max_length=50)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001
    model = models.CharField(max_length=100, blank=True, null=True)  # noqa: DJ001
    serial_number = models.CharField(unique=True, max_length=100, blank=True, null=True)
    calibration_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    measurement_range_max = models.FloatField(blank=True, null=True)
    send_interval_seconds = models.IntegerField(blank=True, null=True)
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
        managed = TESTING

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
        managed = TESTING

    def __str__(self):
        return f"{self.pollutant.symbol} - {self.norm_type} ({self.threshold_value})"


class AnomalyLog(models.Model):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (DISMISSED, "Dismissed"),
    ]

    description = models.CharField(max_length=255)
    detected_at = models.DateTimeField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=PENDING)
    severity = models.CharField(max_length=20, default="warning")  # warning or critical
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, db_column="sensorid")

    class Meta:
        db_table = "anomalylog"
        managed = TESTING

    def __str__(self):
        return f"Anomaly: {self.description[:30]}..."




class AnomalyRule(models.Model):
    """
    Per-pollutant anomaly detection rules.
    """

    pollutant = models.OneToOneField(
        Pollutant,
        on_delete=models.CASCADE,
        db_column="pollutantid",
        related_name="anomaly_rule",
    )
    is_enabled = models.BooleanField(default=True)
    warning_threshold = models.FloatField(help_text="Warning threshold in μg/m³")
    critical_threshold = models.FloatField(help_text="Critical threshold in μg/m³")
    sudden_change_enabled = models.BooleanField(default=True)
    sudden_change_percent = models.FloatField(
        default=50, help_text="Trigger if value changes by this % in sudden_change_minutes"
    )
    sudden_change_minutes = models.IntegerField(
        default=10, help_text="Time window for sudden change detection"
    )

    class Meta:
        db_table = "anomalyrule"
        managed = TESTING

    def __str__(self):
        return f"Rule for {self.pollutant.symbol}"


class GlobalAnomalyConfig(models.Model):
    """
    Global anomaly detection configuration (singleton).
    """

    missing_data_timeout_minutes = models.IntegerField(
        default=30, help_text="Alert if sensor doesn't send data for this many minutes"
    )

    class Meta:
        db_table = "globalanomalyconfig"
        managed = TESTING

    def __str__(self):
        return "Global Anomaly Config"

    @classmethod
    def get_config(cls):
        """Get or create the singleton config instance."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

