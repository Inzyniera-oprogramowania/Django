import sys
from django.conf import settings
from django.contrib.gis.db import models as geomodels
from django.db import models

TESTING = "pytest" in sys.modules


class ForecastArea(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=100)
    h3_cells = models.JSONField(blank=True, null=True)
    geom = geomodels.PolygonField(blank=True, null=True, srid=4326)

    class Meta:
        db_table = "forecastarea"
        managed = TESTING

    def __str__(self):
        return self.name


class Forecast(models.Model):
    id = models.BigAutoField(primary_key=True)
    forecast_date = models.DateField(auto_now_add=True)
    time_horizon = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    forecast_area = models.ForeignKey(
        ForecastArea,
        on_delete=models.CASCADE,
        db_column="forecastareaid",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="userid",
    )

    class Meta:
        db_table = "forecast"
        managed = TESTING

    def __str__(self):
        return f"Forecast for {self.forecast_area.name} on {self.forecast_date}"


class ForecastPollutant(models.Model):
    id = models.BigAutoField(primary_key=True)
    forecast_timestamp = models.DateTimeField()
    predicted_value = models.FloatField()
    uncertainty = models.FloatField(blank=True, null=True)

    forecast = models.ForeignKey(
        Forecast,
        on_delete=models.CASCADE,
        db_column="forecastid",
    )
    pollutant = models.ForeignKey(
        "sensors.Pollutant",
        on_delete=models.RESTRICT,
        db_column="pollutantid",
    )

    class Meta:
        db_table = "forecastpollutant"
        managed = TESTING
        constraints = [
            models.UniqueConstraint(
                fields=['forecast', 'pollutant', 'forecast_timestamp'],
                name='idx_forecast_unique_point'
            )
        ]

    def __str__(self):
        return f"{self.pollutant} in {self.forecast} at {self.forecast_timestamp}"
