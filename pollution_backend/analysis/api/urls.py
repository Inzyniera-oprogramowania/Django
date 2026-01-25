"""
URL configuration for analysis API.
"""
from django.urls import path

from .views import RunAnalysisView, AnalysisTypesView, QuickStatsView

app_name = "analysis"

urlpatterns = [
    path("run/", RunAnalysisView.as_view(), name="run"),
    path("types/", AnalysisTypesView.as_view(), name="types"),
    path("quick-stats/", QuickStatsView.as_view(), name="quick-stats"),
]
