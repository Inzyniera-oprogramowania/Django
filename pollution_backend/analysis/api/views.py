"""
API views for data analysis endpoints.
"""
from dataclasses import asdict

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from pollution_backend.sensors.models import Sensor
from pollution_backend.analysis.services import (
    get_descriptive_stats,
    get_trend_analysis,
    get_period_comparison,
    get_norm_exceedance_analysis,
)
from .serializers import (
    AnalysisRequestSerializer,
    DescriptiveStatsSerializer,
    TrendAnalysisSerializer,
    PeriodComparisonSerializer,
    NormExceedanceSerializer,
    AnalysisResponseSerializer,
)


class RunAnalysisView(APIView):
    """
    Run data analysis based on specified parameters.
    
    POST /api/analysis/run/
    """
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production

    def post(self, request):
        serializer = AnalysisRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        sensor_id = data["sensor_id"]
        analysis_type = data["analysis_type"]
        date_from = data["date_from"]
        date_to = data["date_to"]

        # Get sensor info
        try:
            sensor = Sensor.objects.select_related(
                "pollutant", 
                "monitoring_station",
                "monitoring_station__location"
            ).get(id=sensor_id)
            
            sensor_info = {
                "id": sensor.id,
                "type": sensor.sensor_type,
                "serial_number": sensor.serial_number,
                "pollutant": sensor.pollutant.symbol if sensor.pollutant else None,
                "pollutant_name": sensor.pollutant.name if sensor.pollutant else None,
                "station_code": sensor.monitoring_station.station_code if sensor.monitoring_station else None,
                "location": sensor.monitoring_station.location.full_address if sensor.monitoring_station and sensor.monitoring_station.location else None,
            }
        except Sensor.DoesNotExist:
            return Response(
                {"error": f"Czujnik o ID {sensor_id} nie istnieje"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Execute analysis based on type
        results = None
        result_serializer = None

        if analysis_type == "descriptive":
            results = get_descriptive_stats(sensor_id, date_from, date_to)
            if results:
                result_serializer = DescriptiveStatsSerializer(asdict(results))

        elif analysis_type == "trend":
            aggregation = data.get("aggregation", "hour")
            results = get_trend_analysis(sensor_id, date_from, date_to, aggregation)
            if results:
                result_serializer = TrendAnalysisSerializer(asdict(results))

        elif analysis_type == "comparison":
            period2_from = data["period2_from"]
            period2_to = data["period2_to"]
            results = get_period_comparison(
                sensor_id, date_from, date_to, period2_from, period2_to
            )
            if results:
                result_serializer = PeriodComparisonSerializer(asdict(results))

        elif analysis_type == "exceedance":
            results = get_norm_exceedance_analysis(sensor_id, date_from, date_to)
            if results:
                result_serializer = NormExceedanceSerializer(asdict(results))

        if results is None:
            return Response(
                {"error": "Brak danych dla wybranych parametrów"},
                status=status.HTTP_404_NOT_FOUND
            )

        response_data = {
            "analysis_type": analysis_type,
            "sensor_id": sensor_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "sensor_info": sensor_info,
            "results": result_serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class AnalysisTypesView(APIView):
    """
    Get available analysis types.
    
    GET /api/analysis/types/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        types = [
            {
                "value": "descriptive",
                "label": "Statystyki opisowe",
                "description": "Średnia, min, max, mediana, odchylenie standardowe, percentyle",
            },
            {
                "value": "trend",
                "label": "Analiza trendów",
                "description": "Kierunek zmian w czasie, wykres liniowy, % zmiany",
            },
            {
                "value": "comparison",
                "label": "Porównanie okresów",
                "description": "Porównanie dwóch zakresów czasowych",
            },
            {
                "value": "exceedance",
                "label": "Przekroczenia norm",
                "description": "Analiza przekroczeń norm jakości powietrza",
            },
        ]
        return Response(types)


class QuickStatsView(APIView):
    """
    Get quick statistics for a sensor (for dashboard/preview).
    
    GET /api/analysis/quick-stats/?sensor_id=1&days=7
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from datetime import datetime, timedelta
        
        sensor_id = request.query_params.get("sensor_id")
        days = int(request.query_params.get("days", 7))
        
        if not sensor_id:
            return Response(
                {"error": "sensor_id jest wymagany"},
                status=status.HTTP_400_BAD_REQUEST
            )

        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)

        stats = get_descriptive_stats(int(sensor_id), date_from, date_to)
        trend = get_trend_analysis(int(sensor_id), date_from, date_to, "day")

        if not stats:
            return Response(
                {"error": "Brak danych"},
                status=status.HTTP_404_NOT_FOUND
            )

        response = {
            "sensor_id": int(sensor_id),
            "period_days": days,
            "avg": stats.mean,
            "min": stats.min_value,
            "max": stats.max_value,
            "unit": stats.unit,
            "trend": trend.trend_direction if trend else "unknown",
            "percent_change": trend.percent_change if trend else 0,
        }

        return Response(response)
