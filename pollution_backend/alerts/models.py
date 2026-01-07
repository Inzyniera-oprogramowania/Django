from django.db import models
from django.conf import settings

class Alert(models.Model):
    level = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField()
    end_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()
    quality_norm = models.ForeignKey('sensors.QualityNorm', on_delete=models.RESTRICT, db_column='qualitynormid')
    forecast_area = models.ForeignKey('forecasts.ForecastArea', on_delete=models.CASCADE, db_column='forecastareaid')

    class Meta:
        db_table = 'alert'
        managed = False

class AlertRecipient(models.Model):
    is_read = models.BooleanField(blank=True, null=True)
    sent_at = models.DateTimeField()
    read_at = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='userid')
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, db_column='alertid')

    class Meta:
        db_table = 'alertrecipient'
        managed = False