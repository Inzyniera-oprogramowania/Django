from django.contrib import admin

from .models import ModelValidationRun, ValidationMetric, ValidationErrorLog


class ValidationMetricInline(admin.TabularInline):
    model = ValidationMetric
    extra = 0
    raw_id_fields = ("pollutant",)


class ValidationErrorLogInline(admin.TabularInline):
    model = ValidationErrorLog
    extra = 0
    raw_id_fields = ("pollutant",)
    readonly_fields = ("error_diff",)
    can_delete = False
    show_change_link = True


@admin.register(ModelValidationRun)
class ModelValidationRunAdmin(admin.ModelAdmin):
    list_display = ("name", "model_name", "executed_at", "user", "data_start_time", "id")
    list_filter = ("model_name", "executed_at", "user")
    search_fields = ("name", "user__username", "user__email", "forecast_area__name")
    inlines = [ValidationMetricInline, ValidationErrorLogInline]
    raw_id_fields = ("user", "forecast_area")
    date_hierarchy = "executed_at"


@admin.register(ValidationMetric)
class ValidationMetricAdmin(admin.ModelAdmin):
    list_display = ("metric_name", "metric_value", "pollutant", "model_validation_run")
    list_filter = ("metric_name", "pollutant")
    search_fields = ("model_validation_run__name",)
    raw_id_fields = ("model_validation_run", "pollutant")


@admin.register(ValidationErrorLog)
class ValidationErrorLogAdmin(admin.ModelAdmin):
    list_display = ("time", "pollutant", "error_diff", "predicted_value", "actual_value", "model_validation_run")
    list_filter = ("pollutant", "time")
    search_fields = ("model_validation_run__name",)
    raw_id_fields = ("model_validation_run", "pollutant")
    readonly_fields = ("error_diff",)
    date_hierarchy = "time"
