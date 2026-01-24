from django.apps import AppConfig


class MeasurementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    name = "pollution_backend.measurements"

    def ready(self):
        try:
            import pollution_backend.measurements.signals
        except ImportError:
            pass
