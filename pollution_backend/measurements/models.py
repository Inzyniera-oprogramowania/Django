from django.contrib.gis.db import models


class Measurement(models.Model):
    time = models.DateTimeField(db_index=True)
    sensor_id = models.BigIntegerField(db_index=True)
    value = models.FloatField()
    unit = models.CharField(max_length=15)

    class Meta:
        db_table = "measurement"
        unique_together = ("time", "sensor_id")


class SystemLog(models.Model):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

    LOG_TYPE_CHOICES = [
        (INFO, "Info"),
        (WARNING, "Warning"),
        (ERROR, "Error"),
        (SUCCESS, "Success")
    ]

    event_type = models.CharField(max_length=50)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    log_level = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default=INFO)
    sensor_id = models.IntegerField(null=True, blank=True, db_index=True)
    station_id = models.IntegerField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        "users.User", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="system_logs",
        db_constraint=False
    )

    class Meta:
        db_table = "systemlog"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp}] {self.event_type}: {self.message}]"

