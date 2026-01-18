from django.urls import path

from .views import TriggerForecastView

urlpatterns = [
    path('generate/', TriggerForecastView.as_view(), name='generate-forecast'),
]
