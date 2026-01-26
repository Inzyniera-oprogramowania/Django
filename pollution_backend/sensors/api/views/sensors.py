from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from pollution_backend.sensors.models import Sensor, Pollutant, QualityNorm
from pollution_backend.measurements.models import SystemLog
from pollution_backend.selectors.sensors import get_active_sensors, get_pollutants, get_norms
from pollution_backend.services.sensors import SensorService
from pollution_backend.sensors.api.serializers import (
    SensorSerializer, SensorCreateSerializer, SensorDropdownSerializer,
    PollutantSerializer, QualityNormSerializer
)
from pollution_backend.sensors.api.pagination import DevicePagination

class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    pagination_class = DevicePagination

    def get_serializer_class(self):
        if self.action == "create": return SensorCreateSerializer
        if self.action == "dropdown": return SensorDropdownSerializer
        return SensorSerializer

    def get_queryset(self):
        if self.action != "list":
            return Sensor.objects.all().select_related("pollutant", "monitoring_station")

        queryset = get_active_sensors()
        station_id = self.request.query_params.get("station_id")
        if station_id:
            try: queryset = queryset.filter(monitoring_station_id=int(station_id))
            except ValueError: pass
        
        pollutant = self.request.query_params.get("pollutant")
        if pollutant: queryset = queryset.filter(pollutant__symbol__iexact=pollutant)
        
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(sensor_type__icontains=search) | queryset.filter(serial_number__icontains=search)
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "false":
                queryset = Sensor.objects.filter(is_active=False).select_related("pollutant", "monitoring_station")
            elif is_active.lower() == "all":
                queryset = Sensor.objects.all().select_related("pollutant", "monitoring_station")
        return queryset

    @action(detail=False, url_path="dropdown")
    def dropdown(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = SensorDropdownSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="reset")
    def reset(self, request, pk=None):
        sensor = self.get_object()
        status = SensorService.reset_sensor(sensor)
        return Response({"status": "reset", "last_reset_at": status.last_reset_at.isoformat()})

    def perform_create(self, serializer):
        sensor = serializer.save()
        SensorService.invalidate_device_list_cache()
        pollutant_name = sensor.pollutant.symbol if sensor.pollutant else "Unknown"
        SensorService.log_sensor_action(
            sensor, "SENSOR_ADDED", 
            f"Sensor {pollutant_name} (SN: {sensor.serial_number}) added", 
            SystemLog.INFO
        )

    def perform_update(self, serializer):
        sensor = serializer.save()
        SensorService.invalidate_device_list_cache()
        pollutant_name = sensor.pollutant.symbol if sensor.pollutant else "Unknown"
        msg = f"Sensor {pollutant_name} updated"
        SensorService.log_sensor_action(sensor, "SENSOR_UPDATED", msg, SystemLog.INFO)

    def perform_destroy(self, instance):
        SensorService.log_sensor_action(
            instance, "SENSOR_REMOVED", 
            f"Sensor removed", 
            SystemLog.WARNING
        )
        super().perform_destroy(instance)
        SensorService.invalidate_device_list_cache()

class PollutantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pollutant.objects.all()
    serializer_class = PollutantSerializer
    pagination_class = None
    def get_queryset(self): return get_pollutants()

class QualityNormViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QualityNorm.objects.all()
    serializer_class = QualityNormSerializer
    pagination_class = None
    def get_queryset(self): return get_norms()