from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ForecastRequestSerializer
from ...services.forecast_lambda_invocation import invoke_forecast_lambda


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
