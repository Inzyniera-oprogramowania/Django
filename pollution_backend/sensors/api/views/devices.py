from rest_framework import viewsets
from rest_framework.response import Response
from pollution_backend.sensors.api.pagination import DevicePagination
from pollution_backend.sensors.api.serializers import DeviceSerializer
from pollution_backend.selectors.devices import get_aggregated_device_list
from pollution_backend.services.redis_cache import DeviceListCache
from rest_framework.permissions import IsAdminUser

class DeviceViewSet(viewsets.GenericViewSet):
    pagination_class = DevicePagination
    permission_classes = [IsAdminUser]

    def list(self, request):
        filter_params = {
            "type": request.query_params.get("type", "station"),
            "search": request.query_params.get("search", "").strip(),
            "id": request.query_params.get("id", "").strip(),
            "pollutant": request.query_params.get("pollutant", "").strip(),
            "is_active": request.query_params.get("is_active"),
            "page": request.query_params.get("page", 1),
            "page_size": request.query_params.get("page_size", 50),
            "sort": request.query_params.get("sort", "id"),
            "order": request.query_params.get("order", "asc")
        }

        cached_response = DeviceListCache.get(filter_params)
        if cached_response:
            return Response(cached_response)

        devices = get_aggregated_device_list(filter_params)
        
        sort_field = filter_params["sort"]
        reverse = filter_params["order"] == "desc"
        
        if sort_field == "is_active":
            devices.sort(key=lambda x: x.get("is_active", False), reverse=reverse)
        elif sort_field == "pollutants":
            devices.sort(key=lambda x: ", ".join(x.get("pollutants", [])).lower(), reverse=reverse)
        else:
            devices.sort(key=lambda x: str(x.get(sort_field, "")).lower(), reverse=reverse)

        page_obj = self.paginate_queryset(devices)
        serializer = DeviceSerializer(page_obj, many=True)
        response = self.get_paginated_response(serializer.data)
        
        DeviceListCache.set(filter_params, response.data)
        
        return response