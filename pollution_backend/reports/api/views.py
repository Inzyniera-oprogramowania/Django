from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from pollution_backend.reports.api.serializers import DataExportRequestSerializer
from pollution_backend.services.reports import ExportService
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse as HTTPResponse

class MeasurementExportView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DataExportRequestSerializer

    @extend_schema(
        parameters=[DataExportRequestSerializer],
        responses={200: bytes, 404:dict, 400: dict},
        description="Exports measurement data in the specified format based on the provided filters."
    )
    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        service = ExportService(serializer.validated_data)
        result = service.generate_file()

        if result is None:
            return Response({"detail": "No data found for the given filters."}, status=status.HTTP_404_NOT_FOUND)
        
        content, content_type, filename,checksum = result
        response = HTTPResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Checksum-SHA256'] = checksum

        return response 