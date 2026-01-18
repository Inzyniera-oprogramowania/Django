from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from .models import ForecastArea, Forecast, ForecastPollutant


@admin.register(ForecastArea)
class ForecastAreaAdmin(gis_admin.GISModelAdmin):
    list_display = ("name", "id")
    search_fields = ("name",)


class ForecastPollutantInline(admin.TabularInline):
    model = ForecastPollutant
    extra = 0
    raw_id_fields = ("pollutant",)


@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ("forecast_area", "forecast_date", "user", "created_at", "id")
    list_filter = ("forecast_date", "created_at", "forecast_area")
    search_fields = ("forecast_area__name", "user__username", "user__email")
    inlines = [ForecastPollutantInline]
    raw_id_fields = ("user", "forecast_area")


@admin.register(ForecastPollutant)
class ForecastPollutantAdmin(admin.ModelAdmin):
    list_display = ("forecast", "pollutant", "forecast_timestamp", "predicted_value", "uncertainty")
    list_filter = ("pollutant", "forecast_timestamp")
    search_fields = ("forecast__forecast_area__name",)
    raw_id_fields = ("forecast", "pollutant")
