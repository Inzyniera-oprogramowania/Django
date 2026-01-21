from django.urls import path

from .views import TriggerForecastView, ForecastListView, ForecastDetailView, ForecastAreaListView

urlpatterns = [
    path('', ForecastListView.as_view(), name='forecast-list'),
    path('areas/', ForecastAreaListView.as_view(), name='forecast-areas'),
    path('<int:id>/', ForecastDetailView.as_view(), name='forecast-detail'),
    path('generate/', TriggerForecastView.as_view(), name='generate-forecast'),
]

