from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from pollution_backend.analysis.strategies import AnalysisStrategy
from pollution_backend.selectors.analysis import get_sensor_with_details
from pollution_backend.services.statistics import get_descriptive_stats, get_trend_analysis
from pollution_backend.analysis.api.serializers import (
    AnalysisRequestSerializer,
    AnalysisResponseSerializer,
    QuickStatsRequestSerializer,
    SensorInfoSerializer
)

class RunAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AnalysisRequestSerializer,
        responses={200: AnalysisResponseSerializer}
    )
    def post(self, request):
        serializer = AnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sensor = get_sensor_with_details(data["sensor_id"])
        sensor_info = SensorInfoSerializer(sensor).data

        try:
            result_obj, result_serializer_cls = AnalysisStrategy.run(data["analysis_type"], data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if not result_obj:
            return Response(
                {"error": "No data available for selected parameters"},
                status=status.HTTP_404_NOT_FOUND
            )

        results_data = AnalysisStrategy.serialize_result(result_obj, result_serializer_cls)

        response_data = {
            "analysis_type": data["analysis_type"],
            "sensor_id": data["sensor_id"],
            "date_from": data["date_from"].isoformat(),
            "date_to": data["date_to"].isoformat(),
            "sensor_info": sensor_info,
            "results": results_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class QuickStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("sensor_id", int, required=True),
            OpenApiParameter("days", int, required=False),
        ],
        responses={200: dict}
    )
    def get(self, request):
        serializer = QuickStatsRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        sensor_id = serializer.validated_data["sensor_id"]
        days = serializer.validated_data["days"]
        
        date_to = timezone.now()
        date_from = date_to - timezone.timedelta(days=days)

        stats = get_descriptive_stats(sensor_id, date_from, date_to)
        trend = get_trend_analysis(sensor_id, date_from, date_to, "day")

        if not stats:
            return Response({
                "sensor_id": sensor_id,
                "status": "no_data",
                "msg": "No data available"
            })

        response = {
            "sensor_id": sensor_id,
            "period_days": days,
            "avg": stats.mean,
            "min": stats.min_value,
            "max": stats.max_value,
            "unit": stats.unit,
            "trend": trend.trend_direction if trend else "unknown",
            "percent_change": trend.percent_change if trend else 0.0,
        }

        return Response(response)


class AnalysisTypesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        types = [
            {"value": "descriptive", "label": "Statystyki opisowe", "description": "Średnia, min, max, mediana, odchylenie standardowe"},
            {"value": "trend", "label": "Analiza trendów", "description": "Kierunek zmian w czasie, wykres liniowy"},
            {"value": "comparison", "label": "Porównanie okresów", "description": "Porównanie dwóch zakresów czasowych"},
            {"value": "exceedance", "label": "Przekroczenia norm", "description": "Analiza przekroczeń norm jakości"},
        ]
        return Response(types)