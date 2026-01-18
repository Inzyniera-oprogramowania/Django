from django.urls import path

from .views import (
    TriggerValidationView,
    ValidationRunListView,
    ValidationRunDetailView
)

urlpatterns = [
    path('', ValidationRunListView.as_view(), name='validation-run-list'),
    path('<int:id>/', ValidationRunDetailView.as_view(), name='validation-run-detail'),
    path('generate/', TriggerValidationView.as_view(), name='trigger-validation'),
]
