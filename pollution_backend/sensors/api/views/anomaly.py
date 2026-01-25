from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters

from pollution_backend.sensors.models import AnomalyLog, AnomalyRule, GlobalAnomalyConfig
from pollution_backend.sensors.api.serializers import (
    AnomalyLogSerializer, 
    AnomalyRuleSerializer, 
    GlobalAnomalyConfigSerializer
)
from pollution_backend.sensors.api.filters import AnomalyLogFilter
from pollution_backend.sensors.api.pagination import DevicePagination


class AnomalyLogViewSet(viewsets.ModelViewSet):
    queryset = AnomalyLog.objects.all()
    serializer_class = AnomalyLogSerializer
    pagination_class = DevicePagination
    filterset_class = AnomalyLogFilter
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["detected_at", "status", "sensor__id"]
    ordering = ["-detected_at"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return AnomalyLog.objects.select_related(
            "sensor",
            "sensor__monitoring_station",
            "sensor__pollutant",
        )


class AnomalyRuleViewSet(viewsets.ModelViewSet):
    queryset = AnomalyRule.objects.all()
    serializer_class = AnomalyRuleSerializer
    pagination_class = None
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return AnomalyRule.objects.select_related("pollutant").order_by("pollutant__symbol")


class GlobalAnomalyConfigViewSet(viewsets.ModelViewSet):
    queryset = GlobalAnomalyConfig.objects.all()
    serializer_class = GlobalAnomalyConfigSerializer
    pagination_class = None
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        GlobalAnomalyConfig.get_config()
        return GlobalAnomalyConfig.objects.all()