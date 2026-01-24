import requests
import time
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from pollution_backend.selectors.sensors import get_active_sensors
from pollution_backend.selectors.sensors import get_active_stations
from pollution_backend.selectors.sensors import get_all_stations
from pollution_backend.selectors.sensors import get_norms
from pollution_backend.selectors.sensors import get_pollutants
from pollution_backend.sensors.models import AnomalyLog
from pollution_backend.sensors.models import AnomalyRule
from pollution_backend.sensors.models import GlobalAnomalyConfig
from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.sensors.models import Pollutant
from pollution_backend.sensors.models import QualityNorm
from pollution_backend.sensors.models import Sensor

from .serializers import AnomalyLogSerializer
from .serializers import AnomalyRuleSerializer
from .serializers import GlobalAnomalyConfigSerializer
from .serializers import MonitoringStationDetailSerializer
from .serializers import MonitoringStationFlatSerializer
from .serializers import MonitoringStationGeoSerializer
from .serializers import PollutantSerializer
from .serializers import QualityNormSerializer
from .serializers import SensorSerializer
from .serializers import StationDropdownSerializer
from .serializers import SensorDropdownSerializer




from drf_spectacular.utils import extend_schema
from django.core.cache import cache
import hashlib
import json


def get_device_list_cache_key(params_dict):
    cache_key_base = json.dumps(params_dict, sort_keys=True)
    cache_key_hash = hashlib.md5(cache_key_base.encode()).hexdigest()
    return f"devices:list:{cache_key_hash}"


def invalidate_device_list_cache():
    cache_version_key = "devices:list:version"
    current_version = cache.get(cache_version_key, 0)
    cache.set(cache_version_key, current_version + 1, timeout=None)


def broadcast_station_log(station_id, log):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"station_{station_id}_status",
                {
                    "type": "system_log",
                    "data": {
                        "msg_type": "log",
                        "id": log.id,
                        "station_id": station_id,
                        "event_type": log.event_type,
                        "message": log.message,
                        "log_level": log.log_level,
                        "timestamp": log.timestamp.isoformat()
                    }
                }
            )
    except Exception as e:
        print(f"Failed to broadcast station log: {e}")


class DevicePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class MonitoringStationViewSet(viewsets.ModelViewSet):
    queryset = MonitoringStation.objects.all()
    pagination_class = DevicePagination

    @extend_schema(exclude=True)
    def list(self, request, *args, **kwargs):
         return super().list(request, *args, **kwargs)

    @action(detail=False, url_path="all")
    def all_stations(self, request):
        queryset = self.filter_queryset(get_all_stations())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, url_path="dropdown")
    def dropdown(self, request):
        """Optimized endpoint for station dropdowns."""
        queryset = self.filter_queryset(get_active_stations())
        # Disable pagination for dropdowns
        serializer = StationDropdownSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = get_active_stations()
        
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                station_code__icontains=search
            ) | queryset.filter(
                location__full_address__icontains=search
            )
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "false":
                queryset = MonitoringStation.objects.filter(is_active=False).select_related("location")
            elif is_active.lower() == "all":
                queryset = get_all_stations()
        
        return queryset

    def get_object(self):
        station_id = self.kwargs.get("pk")
        return get_object_or_404(get_active_stations(), pk=station_id)

    def get_serializer_class(self):
        if self.action == "create":
            from .serializers import StationCreateSerializer
            return StationCreateSerializer
        if self.action == "list":
            return MonitoringStationGeoSerializer
        if self.action == "all_stations":
            return MonitoringStationFlatSerializer
        if self.action == "dropdown":
            return StationDropdownSerializer
        return MonitoringStationDetailSerializer

    @action(detail=False, methods=["post"], url_path="validate_address")
    def validate_address(self, request):
        address = request.data.get("address")
        if not address:
            return Response({"valid": False, "error": "Adres jest wymagany"}, status=400)
            
        import re
        
        geocode_url = "https://nominatim.openstreetmap.org/search"
        
        def clean_addr(a):
            val = re.sub(r'^(ul\.|al\.|os\.|pl\.)\s*', '', a, flags=re.IGNORECASE)
            val = re.sub(r'/\d+[a-zA-Z]*', '', val)
            return val.strip()

        attempts = sorted(list(set([address, clean_addr(address)])), key=len, reverse=True)
        
        last_error = None
        for attempt in attempts:
            try:
                # todo change later
                ua = f"PollutionApp_DEV_{int(time.time())}"
                resp = requests.get(geocode_url, params={
                    "q": attempt,
                    "format": "json",
                    "limit": 1
                }, headers={"User-Agent": ua}, timeout=10)
                
                if resp.status_code == 200 and resp.json():
                    result = resp.json()[0]
                    return Response({
                        "valid": True,
                        "lat": float(result["lat"]),
                        "lon": float(result["lon"]),
                        "display_name": result.get("display_name")
                    })
                elif resp.status_code != 200:
                    last_error = f"Nominatim Error: {resp.status_code}"
            except Exception as e:
                last_error = str(e)
                continue
                
        return Response({"valid": False, "debug_error": last_error})

    def create(self, request, *args, **kwargs):
        from .serializers import StationCreateSerializer
        from pollution_backend.sensors.models import Location
        from django.contrib.gis.geos import Point
        import requests
        
        serializer = StationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        address = serializer.validated_data['address']
        station_code = serializer.validated_data['station_code']
        owner = serializer.validated_data.get('owner', '')
        
        lat = 52.2297
        lon = 21.0122
        display_name = address
        
        try:
            geocode_url = "https://nominatim.openstreetmap.org/search"
            resp = requests.get(geocode_url, params={
                "q": address,
                "format": "json",
                "limit": 1
            }, headers={"User-Agent": "PollutionMonitoringApp/1.0"}, timeout=10)
            
            if resp.status_code == 200 and resp.json():
                results = resp.json()
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                display_name = results[0].get("display_name", address)
        except Exception:
            pass
        
        location = Location.objects.create(
            geom=Point(lon, lat, srid=4326),
            full_address=display_name
        )
        
        station = MonitoringStation.objects.create(
            station_code=station_code,
            owner=owner or None,
            location=location,
            is_active=True
        )
        
        return Response({
            "id": station.id,
            "station_code": station.station_code,
            "address": location.full_address,
            "lat": lat,
            "lon": lon
        }, status=201)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        invalidate_device_list_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        invalidate_device_list_cache()


class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    pagination_class = DevicePagination

    def get_serializer_class(self):
        if self.action == "create":
            from .serializers import SensorCreateSerializer
            return SensorCreateSerializer
        if self.action == "dropdown":
            return SensorDropdownSerializer
        return SensorSerializer

    def get_queryset(self):
        queryset = get_active_sensors()
        
        station_id = self.request.query_params.get("station_id")
        if station_id:
            try:
                queryset = queryset.filter(monitoring_station_id=int(station_id))
            except ValueError:
                pass
        
        pollutant = self.request.query_params.get("pollutant")
        if pollutant:
            queryset = queryset.filter(pollutant__symbol__iexact=pollutant)
        
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(sensor_type__icontains=search) | queryset.filter(
                serial_number__icontains=search
            )
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "false":
                queryset = Sensor.objects.filter(is_active=False).select_related(
                    "pollutant", "monitoring_station"
                )
            elif is_active.lower() == "all":
                queryset = Sensor.objects.all().select_related(
                    "pollutant", "monitoring_station"
                )
        
        return queryset

    @action(detail=False, url_path="dropdown")
    def dropdown(self, request):
        """Optimized endpoint for sensor dropdowns."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = SensorDropdownSerializer(queryset, many=True)
        return Response(serializer.data)
    @action(detail=True, methods=["post"], url_path="reset")
    def reset(self, request, pk=None):
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from django.utils import timezone

        from pollution_backend.sensors.models import DeviceStatus

        sensor = self.get_object()
        status, _ = DeviceStatus.objects.get_or_create(sensor=sensor)
        status.uptime_seconds = 0
        status.last_reset_at = timezone.now()
        status.save()

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"sensor_{pk}_status",
                {
                    "type": "status_update",
                    "data": {
                        "sensor_id": int(pk),
                        "uptime_seconds": 0,
                        "last_reset_at": status.last_reset_at.isoformat(),
                        "reset": True,
                        "battery_percent": 100,
                    },
                },
            )

        try:
            from pollution_backend.measurements.models import SystemLog
            SystemLog.objects.create(
                event_type="DEVICE_RESET",
                message=f"Device reset triggered for Sensor {sensor.id}",
                log_level=SystemLog.WARNING,
                sensor_id=sensor.id,
            )
        except Exception as e:
            print(f"Failed to create SystemLog for reset: {e}")

        try:
            import paho.mqtt.publish as publish
            from django.conf import settings
            
            broker_host = getattr(settings, "MQTT_BROKER_HOST", "mosquitto")
            station_code = sensor.monitoring_station.station_code
            topic = f"sensors/{station_code}/command"
            
            payload = '{"command": "RESET"}'
            publish.single(topic, payload, hostname=broker_host)
        except Exception as e:
             print(f"Failed to publish MQTT reset command: {e}")

        return Response({"status": "reset", "last_reset_at": status.last_reset_at.isoformat()})

    def perform_create(self, serializer):
        sensor = serializer.save()
        invalidate_device_list_cache()
        
        try:
            from pollution_backend.measurements.models import SystemLog
            
            station = sensor.monitoring_station
            pollutant_name = sensor.pollutant.symbol if sensor.pollutant else "Unknown"
            
            log = SystemLog.objects.create(
                station_id=station.id,
                event_type="SENSOR_ADDED",
                message=f"Sensor {pollutant_name} (SN: {sensor.serial_number}) added to station",
                log_level=SystemLog.INFO
            )
            broadcast_station_log(station.id, log)
        except Exception as e:
            print(f"Failed to create station log: {e}")

    def perform_update(self, serializer):
        sensor = serializer.save()
        invalidate_device_list_cache()
        
        try:
            from pollution_backend.measurements.models import SystemLog
            station = sensor.monitoring_station
            pollutant_name = sensor.pollutant.symbol if sensor.pollutant else "Unknown"
            
            if 'is_active' in serializer.validated_data:
                if sensor.is_active:
                    message = f"Sensor {pollutant_name} (SN: {sensor.serial_number}) activated"
                    level = SystemLog.SUCCESS
                else:
                    message = f"Sensor {pollutant_name} (SN: {sensor.serial_number}) deactivated"
                    level = SystemLog.WARNING
            else:
                message = f"Sensor {pollutant_name} (SN: {sensor.serial_number}) configuration updated"
                level = SystemLog.INFO
            
            log = SystemLog.objects.create(
                station_id=station.id,
                event_type="SENSOR_UPDATED",
                message=message,
                log_level=level
            )
            broadcast_station_log(station.id, log)
        except Exception as e:
            print(f"Failed to create station log: {e}")

    def perform_destroy(self, instance):
        station = instance.monitoring_station
        station_id = station.id
        pollutant_name = instance.pollutant.symbol if instance.pollutant else "Unknown"
        serial_number = instance.serial_number
        
        super().perform_destroy(instance)
        invalidate_device_list_cache()
        
        # Log to station
        try:
            from pollution_backend.measurements.models import SystemLog
            log = SystemLog.objects.create(
                station_id=station_id,
                event_type="SENSOR_REMOVED",
                message=f"Sensor {pollutant_name} (SN: {serial_number}) removed from station",
                log_level=SystemLog.WARNING
            )
            broadcast_station_log(station_id, log)
        except Exception as e:
            print(f"Failed to create station log: {e}")


class PollutantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Pollutant.objects.all()
    serializer_class = PollutantSerializer
    pagination_class = None

    def get_queryset(self):
        return get_pollutants()


class QualityNormViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QualityNorm.objects.all()
    serializer_class = QualityNormSerializer
    pagination_class = None

    def get_queryset(self):
        return get_norms()


class DeviceViewSet(viewsets.ViewSet):

    pagination_class = DevicePagination

    def list(self, request):
        from django.db.models import Max
        from pollution_backend.measurements.models import Measurement
        from .serializers import DeviceSerializer
        
        device_type = request.query_params.get("type", "station") 
        search = request.query_params.get("search", "").strip()
        pollutant_filter = request.query_params.get("pollutant", "").strip()
        is_active_param = request.query_params.get("is_active", "all")
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 50)), 200)
        sort_field = request.query_params.get("sort", "id")
        sort_dir = request.query_params.get("order", "asc")
        
        cache_version = cache.get("devices:list:version", 0)
        cache_params = {
            "v": str(cache_version),
            "type": str(device_type),
            "search": str(search),
            "pollutant": str(pollutant_filter),
            "is_active": str(is_active_param),
            "page": str(page),
            "page_size": str(page_size),
            "sort": str(sort_field),
            "order": str(sort_dir)
        }
        cache_key = get_device_list_cache_key(cache_params)
        
        try:
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return Response(cached_response)
        except Exception as e:
            print(f"Cache read error: {e}")

        
        devices = []
        
        is_active_filter = None
        if is_active_param == "true":
            is_active_filter = True
        elif is_active_param == "false":
            is_active_filter = False
        
        sensor_last_times = {}
        try:
            latest_measurements = (
                Measurement.objects
                .values("sensor_id")
                .annotate(last_time=Max("time"))
            )
            sensor_last_times = {m["sensor_id"]: m["last_time"] for m in latest_measurements}
        except Exception:
            pass
        
        if device_type in ("station", "all"):
            stations = get_all_stations()
            if search:
                stations = stations.filter(station_code__icontains=search) | stations.filter(
                    location__full_address__icontains=search
                )
            if pollutant_filter and pollutant_filter != "Wszystkie":
                stations = stations.filter(sensor__pollutant__symbol=pollutant_filter).distinct()
            if is_active_filter is not None:
                stations = stations.filter(is_active=is_active_filter)
            
            stations = stations.prefetch_related("sensor_set")

            for s in stations:
                s_sensors = s.sensor_set.all()
                
                max_time = None
                station_pollutants = set()
                
                for sensor in s_sensors:
                    if sensor.pollutant:
                        station_pollutants.add(sensor.pollutant.symbol)
                        
                    st = sensor_last_times.get(sensor.id)
                    if st:
                        if max_time is None or st > max_time:
                            max_time = st
                
                last_time_str = max_time.strftime("%Y-%m-%d %H:%M") if max_time else "-"
                
                devices.append({
                    "id": s.id,
                    "station_code": s.station_code,
                    "type": "Stacja",
                    "pollutants": sorted(list(station_pollutants)),
                    "address": s.location.full_address if s.location else "Brak danych",
                    "lastLogTime": last_time_str,
                    "is_active": s.is_active,
                })
        
        if device_type in ("sensor", "all"):
            sensors = get_active_sensors() if is_active_filter is None or is_active_filter else Sensor.objects.all()
            sensors = sensors.select_related("pollutant", "monitoring_station", "monitoring_station__location")
            
            if is_active_filter is not None:
                sensors = sensors.filter(is_active=is_active_filter)
            if pollutant_filter and pollutant_filter != "Wszystkie":
                sensors = sensors.filter(pollutant__symbol=pollutant_filter)
            if search:
                sensors = sensors.filter(serial_number__icontains=search) | sensors.filter(
                    sensor_type__icontains=search
                ) | sensors.filter(monitoring_station__station_code__icontains=search)
            
            for s in sensors:
                last_time = sensor_last_times.get(s.id)
                last_time_str = last_time.strftime("%Y-%m-%d %H:%M") if last_time else "-"
                devices.append({
                    "id": s.id,
                    "serial_number": s.serial_number,
                    "type": "Czujnik",
                    "pollutants": [s.pollutant.symbol] if s.pollutant else [],
                    "address": s.monitoring_station.station_code if s.monitoring_station else "Brak danych",
                    "lastLogTime": last_time_str,
                    "is_active": s.is_active,
                })
        
        reverse = sort_dir == "desc"
        if sort_field == "is_active":
            devices.sort(key=lambda x: x.get("is_active", False), reverse=reverse)
        elif sort_field == "pollutants":
            devices.sort(
                key=lambda x: ", ".join(x.get("pollutants", [])).lower(),
                reverse=reverse
            )
        else:
            devices.sort(key=lambda x: str(x.get(sort_field, "")).lower(), reverse=reverse)
        
        total_count = len(devices)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_devices = devices[start:end]
        
        serializer = DeviceSerializer(paginated_devices, many=True)
        
        response_data = {
            "count": total_count,
            "next": None if end >= total_count else f"?page={page + 1}",
            "previous": None if page <= 1 else f"?page={page - 1}",
            "results": serializer.data,
        }
        
        try:
            cache.set(cache_key, response_data, timeout=300)
        except Exception as e:
            pass
        
        return Response(response_data)
class AnomalyLogFilter(filters.FilterSet):
    """Filter for AnomalyLog queryset."""

    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    sensor_id = filters.NumberFilter(field_name="sensor_id")
    detected_at_after = filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="gte"
    )
    detected_at_before = filters.DateTimeFilter(
        field_name="detected_at", lookup_expr="lte"
    )

    class Meta:
        model = AnomalyLog
        fields = ["status", "sensor_id", "detected_at_after", "detected_at_before"]


class AnomalyLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AnomalyLog model.

    Supports:
    - GET /api/anomalies/ - list with filtering
    - GET /api/anomalies/{id}/ - single anomaly details
    - PATCH /api/anomalies/{id}/ - update status
    """

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
    """
    ViewSet for AnomalyRule model.

    Supports:
    - GET /api/anomaly-rules/ - list all rules
    - GET /api/anomaly-rules/{id}/ - single rule details
    - PUT/PATCH /api/anomaly-rules/{id}/ - update rule
    """

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
    """
    ViewSet for GlobalAnomalyConfig (singleton).

    Supports:
    - GET /api/anomaly-config/ - get global config
    - PUT/PATCH /api/anomaly-config/1/ - update global config
    """

    queryset = GlobalAnomalyConfig.objects.all()
    serializer_class = GlobalAnomalyConfigSerializer
    pagination_class = None
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        # Ensure singleton exists
        GlobalAnomalyConfig.get_config()
        return GlobalAnomalyConfig.objects.all()



