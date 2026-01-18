import sys
from django.db import models
from django.conf import settings

TESTING = "pytest" in sys.modules


class ModelValidationRun(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)
    executed_at = models.DateTimeField(auto_now_add=True)
    data_start_time = models.DateTimeField()
    data_end_time = models.DateTimeField()

    forecast_area = models.ForeignKey(
        'forecasts.ForecastArea',
        on_delete=models.CASCADE,
        db_column='forecastareaid'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='userid'
    )

    class Meta:
        db_table = 'modelvalidationrun'
        managed = TESTING

    def __str__(self):
        return f"{self.name} ({self.model_name})"


class ValidationMetric(models.Model):
    id = models.BigAutoField(primary_key=True)
    metric_name = models.CharField(max_length=50)
    metric_value = models.FloatField()

    pollutant = models.ForeignKey(
        'sensors.Pollutant',
        on_delete=models.RESTRICT,
        db_column='pollutantid'
    )
    model_validation_run = models.ForeignKey(
        ModelValidationRun,
        on_delete=models.CASCADE,
        db_column='modelvalidationrunid',
        related_name='metrics'
    )

    class Meta:
        db_table = 'validationmetric'
        managed = TESTING

    def __str__(self):
        return f"{self.metric_name}: {self.metric_value} ({self.pollutant.symbol})"


class ValidationErrorLog(models.Model):
    time = models.DateTimeField(primary_key=True)
    predicted_value = models.FloatField()
    actual_value = models.FloatField()
    error_diff = models.FloatField(editable=False)

    model_validation_run = models.ForeignKey(
        ModelValidationRun,
        on_delete=models.CASCADE,
        db_column='modelvalidationrunid',
        related_name='error_logs'
    )
    pollutant = models.ForeignKey(
        'sensors.Pollutant',
        on_delete=models.RESTRICT,
        db_column='pollutantid'
    )

    class Meta:
        db_table = 'validationerrorlog'
        managed = TESTING
        verbose_name = "Validation Error Log"
        verbose_name_plural = "Validation Error Logs"
        ordering = ['-time']

    def __str__(self):
        return f"Error {self.error_diff} at {self.time}"
