from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from pollution_backend.reports.api.serializers import DataExportRequestSerializer, ReportIssueCreateSerializer
from pollution_backend.services.reports import ExportService
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse as HTTPResponse
from rest_framework import generics

class MeasurementExportView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DataExportRequestSerializer

    @extend_schema(
        request=DataExportRequestSerializer,
        responses={200: bytes, 404:dict, 400: dict},
        description="Exports measurement data in the specified format based on the provided filters."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        service = ExportService(serializer.validated_data, user=request.user)
        result = service.execute_and_save()

        if result is None:
            return Response({"detail": "No data found for the given filters."}, status=status.HTTP_404_NOT_FOUND)
        
        content = result['content']
        content_type = result['content_type']
        filename = result['filename']
        checksum = result['checksum']

        response = HTTPResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Checksum-SHA256'] = checksum

        return response 

class ReportIssueCreateView(generics.CreateAPIView):
    serializer_class = ReportIssueCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        report_id = self.kwargs.get('report_id')
        report = Report.objects.get(id=report_id)

        serializer.save(
            report=report,
            user=self.request.user
        )