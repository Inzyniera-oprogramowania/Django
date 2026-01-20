from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ValidationRequestSerializer,
    ValidationRunListSerializer,
    ValidationRunDetailSerializer
)
from ..models import ModelValidationRun
from ...services.aws_lambda import invoke_validation_lambda, LambdaInvocationError


class TriggerValidationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidationRequestSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            try:
                invoke_validation_lambda(
                    user_id=request.user.id,
                    model_name=data.get('model_name'),
                    run_name=data.get('run_name')
                )

                return Response(
                    {
                        "message": "Validation run triggered successfully. Results will appear in the list once processed."},
                    status=status.HTTP_202_ACCEPTED
                )

            except LambdaInvocationError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidationRunListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ValidationRunListSerializer

    def get_queryset(self):
        return ModelValidationRun.objects.filter(
            user=self.request.user
        ).order_by('-executed_at')


class ValidationRunDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ValidationRunDetailSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return ModelValidationRun.objects.filter(
            user=self.request.user
        ).prefetch_related(
            'metrics',
            'metrics__pollutant',
            'error_logs',
            'error_logs__pollutant'
        )
