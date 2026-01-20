from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ForecastRequestSerializer, ForecastListSerializer, ForecastDetailSerializer, ForecastAreaSerializer
from ..models import Forecast, ForecastArea
from ...services.aws_lambda import invoke_forecast_lambda, LambdaInvocationError


class ForecastAreaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ForecastAreaSerializer
    pagination_class = None

    def get_queryset(self):
        return ForecastArea.objects.all().order_by('name')


class TriggerForecastView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ForecastRequestSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            try:
                invoke_forecast_lambda(
                    user_id=request.user.id,
                    h3_index=data['h3_index'],
                    pollutants=data['pollutants'],
                    model_name=data.get('model_name')
                )

                return Response(
                    {"message": "Forecast generation started successfully."},
                    status=status.HTTP_202_ACCEPTED
                )

            except LambdaInvocationError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForecastListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ForecastListSerializer

    def get_queryset(self):
        return Forecast.objects.filter(
            user=self.request.user
        ).select_related('forecast_area').order_by('-created_at')


class ForecastDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ForecastDetailSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Forecast.objects.filter(
            user=self.request.user
        ).select_related(
            'forecast_area'
        ).prefetch_related(
            'forecastpollutant_set',
            'forecastpollutant_set__pollutant'
        )
