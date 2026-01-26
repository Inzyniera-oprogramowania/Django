from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from pollution_backend.sensors.models import MonitoringStation
from pollution_backend.selectors.sensors import get_active_stations, get_all_stations
from pollution_backend.services.stations import StationService
from pollution_backend.services.sensors import SensorService
from pollution_backend.sensors.api.serializers import (
    MonitoringStationDetailSerializer,
    MonitoringStationGeoSerializer,
    MonitoringStationFlatSerializer,
    StationDropdownSerializer,
    StationCreateSerializer
)
from pollution_backend.sensors.api.pagination import DevicePagination

class MonitoringStationViewSet(viewsets.ModelViewSet):
    queryset = MonitoringStation.objects.all()
    pagination_class = DevicePagination

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAdminUser()]

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
        queryset = self.filter_queryset(get_active_stations())
        serializer = StationDropdownSerializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        if self.action != "list":
            return MonitoringStation.objects.all().select_related("location")
            
        queryset = get_active_stations()
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(station_code__icontains=search) | queryset.filter(location__full_address__icontains=search)
        
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "false":
                queryset = MonitoringStation.objects.filter(is_active=False).select_related("location")
            elif is_active.lower() == "all":
                queryset = get_all_stations()
        return queryset

    def get_serializer_class(self):
        if self.action == "create": return StationCreateSerializer
        if self.action == "list": return MonitoringStationGeoSerializer
        if self.action == "all_stations": return MonitoringStationFlatSerializer
        if self.action == "dropdown": return StationDropdownSerializer
        return MonitoringStationDetailSerializer

    @action(detail=False, methods=["post"], url_path="validate_address")
    def validate_address(self, request):
        address = request.data.get("address")
        if not address:
             return Response({"valid": False, "error": "Brak adresu"}, status=400)
        result = StationService.geocode_address(address)
        if result:
            return Response({"valid": True, **result})
        return Response({"valid": False, "error": "Nie znaleziono adresu"})

    def create(self, request, *args, **kwargs):
        serializer = StationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        station, geo_data = StationService.create_station(serializer.validated_data)
        return Response({
            "id": station.id,
            "station_code": station.station_code,
            "address": geo_data['display_name'],
            "lat": geo_data['lat'],
            "lon": geo_data['lon']
        }, status=201)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        SensorService.invalidate_device_list_cache()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        SensorService.invalidate_device_list_cache()