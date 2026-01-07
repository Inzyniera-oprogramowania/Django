from django.contrib.gis.db import models


class Measurement(models.Model):
    time = models.DateTimeField(primary_key=True)
    sensor_id = models.BigIntegerField(db_index=True)
    value = models.FloatField()
    unit = models.CharField(max_length=15)

    class Meta:
        db_table = "measurement"
