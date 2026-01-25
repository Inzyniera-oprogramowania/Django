from datetime import datetime
from django.utils.decorators import method_decorator
from django.db import transaction, IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework import mixins
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError   
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from pollution_backend.users.api.permissions import IsAdvancedUser 
from pollution_backend.measurements.api.serializers import (
    AggregatedMeasurementSerializer,
)
from pollution_backend.measurements.api.serializers import MeasurementSerializer, MeasurementImportSerializer
from pollution_backend.users.authentication import ApiKeyAuthentication
from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.selectors.measurements import get_aggregated_measurements
from pollution_backend.selectors.measurements import get_measurements_for_sensor
from pollution_backend.services.measurements import MeasurementImportService
from drf_spectacular.utils import extend_schema

SENSOR_ID_REQUIRED = "sensor_id query parameter is required."


class MeasurementPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 10000


class MeasurementViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Measurement.objects.none()
    serializer_class = MeasurementSerializer
    pagination_class = MeasurementPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Measurement.objects.none()

        sensor_id = self.request.query_params.get("sensor_id")
        if not sensor_id:
            return Measurement.objects.none()

        date_from = self._parse_date(self.request.query_params.get("date_from"))
        date_to = self._parse_date(self.request.query_params.get("date_to"))

        return get_measurements_for_sensor(
            sensor_id=int(sensor_id),
            date_from=date_from,
            date_to=date_to,
        )

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    @action(detail=False, methods=["get"])
    def aggregated(self, request):
        sensor_id = request.query_params.get("sensor_id")
        interval = request.query_params.get("interval", "hour")
        if not sensor_id:
            raise ValidationError(SENSOR_ID_REQUIRED)

        try:
            data = get_aggregated_measurements(
                sensor_id=int(sensor_id),
                interval=interval,
            )
        except ValueError as err:
            raise ValidationError(str(err)) from err

        serializer = AggregatedMeasurementSerializer(data, many=True)
        return Response(serializer.data)


class SystemLogViewSet(viewsets.ModelViewSet):
    from pollution_backend.measurements.models import SystemLog
    from pollution_backend.measurements.api.serializers import SystemLogSerializer
    
    permission_classes = [IsAuthenticated]
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    pagination_class = MeasurementPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        sensor_id = self.request.query_params.get('sensor_id')
        station_id = self.request.query_params.get('station_id')
        
        if sensor_id:
            queryset = queryset.filter(sensor_id=sensor_id)
        if station_id:
            queryset = queryset.filter(station_id=station_id)
            
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
             
        event_types = self.request.query_params.getlist('event_type')
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)

        return queryset

@method_decorator(transaction.non_atomic_requests, name='dispatch')
@method_decorator(transaction.non_atomic_requests(using='timeseries'), name='dispatch')
class MeasurementImportView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'import_data'

    @extend_schema(
        request=MeasurementImportSerializer,
        responses={
            201: None, 
            400: "Błąd parsowania JSON", 
            401: "Nieautoryzowany", 
            422: "Błąd walidacji biznesowej"
        },
        description="Importuje pojedynczy pomiar lub paczkę danych."
    )
    def post(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = MeasurementImportSerializer(data=request.data, many=is_many, context={'request': request})
        
        if not serializer.is_valid():
            return Response(
                {"code": "VALIDATION_ERROR", "errors": serializer.errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            items = serializer.validated_data if is_many else [serializer.validated_data]
            
            for item_data in items:
                service = MeasurementImportService(item_data)
                service.process_import()
            
            if hasattr(request, 'auth') and hasattr(request.auth, 'request_count'):
                request.auth.request_count += 1
                request.auth.save()

            if is_many:
                msg = f"Batch imported {len(items)} measurements."
                sensor_id = items[0]['sensor_id'] if items else None 
            else:
                msg = f"Imported measurement for sensor {items[0]['sensor_id']} at {items[0]['timestamp']}"
                sensor_id = items[0]['sensor_id']

            SystemLog.objects.create(
                event_type="import_success",
                message=msg,
                log_level=SystemLog.SUCCESS,
                sensor_id=sensor_id,
                user=request.user
            )

            return Response(
                {"detail": f"Successfully imported {len(items)} items."}, 
                status=status.HTTP_201_CREATED
            )

        except IntegrityError:
            msg = "Duplikat: Pomiar dla tego sensora z taką samą datą już istnieje."
            SystemLog.objects.create(
                event_type="import_error",
                message=msg,
                log_level=SystemLog.ERROR,
                user=request.user if request.user.is_authenticated else None
            )
            return Response(
                {"detail": msg}, 
                status=status.HTTP_409_CONFLICT
            )

        except Exception as e:
            SystemLog.objects.create(
                event_type="import_error",
                message=str(e),
                log_level=SystemLog.ERROR,
                user=request.user if request.user.is_authenticated else None
            )
            return Response(
                {"detail": "Internal Server Error during processing."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )