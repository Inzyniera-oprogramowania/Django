from django.contrib.gis.db import models as geomodels
from django.db import models


class ForecastArea(models.Model):
    name = models.CharField(unique=True, max_length=100)
    h3_cells = models.JSONField(blank=True, null=True)
    geom = geomodels.PolygonField(blank=True, null=True, srid=4326)

    class Meta:
        db_table = "forecastarea"
        managed = False

    def __str__(self):
        return self.name


class Forecast(models.Model):
    forecast_date = models.DateField()
    time_horizon = models.JSONField()
    created_at = models.DateTimeField()
    forecast_area = models.ForeignKey(
        ForecastArea,
        on_delete=models.CASCADE,
        db_column="forecastareaid",
    )

    class Meta:
        db_table = "forecast"
        managed = False

    def __str__(self):
        return f"Forecast for {self.forecast_area.name} on {self.forecast_date}"


class ForecastPollutant(models.Model):
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
        managed = False

    def __str__(self):
        return f"{self.pollutant} in {self.forecast}"
