from django.contrib import admin
from .models import Measurement, SystemLog

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "event_type", "log_level", "sensor_id", "station_id", "user")
    list_filter = ("event_type", "log_level", "timestamp")
    search_fields = ("message", "event_type", "sensor_id", "station_id")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("time", "sensor_id", "value", "unit")
    list_filter = ("unit", "time")
    search_fields = ("sensor_id",)
    date_hierarchy = "time"
    ordering = ("-time",)
    list_per_page = 50
