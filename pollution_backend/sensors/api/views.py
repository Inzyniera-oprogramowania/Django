import random
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeasurementSerializer
from .serializers import SensorSerializer


def generate_fake_measurement(offset_hours=0):
    """Generuje losowy pomiar"""
    permission_classes = [AllowAny]
    base_time = timezone.now() - timedelta(hours=offset_hours)
    return {
        "timestamp": base_time,
        "pm25": round(random.uniform(10.0, 50.0), 1),
        "pm10": round(random.uniform(20.0, 80.0), 1),
        "temperature": round(random.uniform(15.0, 30.0), 1),
        "humidity": round(random.uniform(30.0, 60.0), 1),
    }


class SensorListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        mock_sensors = [
            {
                "id": 1,
                "name": "Centrum-Warszawa",
                "location_lat": 52.2297,
                "location_lon": 21.0122,
                "status": "active",
            },
            {
                "id": 2,
                "name": "Kraków-Rynek",
                "location_lat": 50.0647,
                "location_lon": 19.9450,
                "status": "warning",
            },
            {
                "id": 3,
                "name": "Gdańsk-Port",
                "location_lat": 54.3520,
                "location_lon": 18.6466,
                "status": "offline",
            },
        ]
        serializer = SensorSerializer(mock_sensors, many=True)
        return Response(serializer.data)


class SensorDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sensor_id):
        mock_sensor = {
            "id": sensor_id,
            "name": f"Sensor-{sensor_id} (Mock)",
            "location_lat": 52.2297,
            "location_lon": 21.0122,
            "status": "active",
        }
        serializer = SensorSerializer(mock_sensor)
        return Response(serializer.data)


class SensorLatestMeasurementView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sensor_id):
        mock_data = generate_fake_measurement(offset_hours=0)
        serializer = MeasurementSerializer(mock_data)
        return Response(serializer.data)


class SensorHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, sensor_id):
        mock_history = [generate_fake_measurement(i) for i in range(24)]
        mock_history.reverse()

        serializer = MeasurementSerializer(mock_history, many=True)
        return Response(serializer.data)
