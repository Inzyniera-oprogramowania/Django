from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from pollution_backend.users.models import AdvancedUser
from pollution_backend.users.api.permissions import IsAdvancedUser
from rest_framework.permissions import IsAuthenticated
from pollution_backend.reports.api.serializers import DataExportRequestSerializer, ReportIssueCreateSerializer
from pollution_backend.services.reports import ExportService
from rest_framework import status, permissions, generics
from drf_spectacular.utils import extend_schema
from django.http import HttpResponse as HTTPResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404

from pollution_backend.measurements.api.serializers import MeasurementSerializer
from pollution_backend.reports.models import Report, ReportIssue

class MeasurementExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdvancedUser]
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
        
        #content = result['content']
        filename = result['filename']
        checksum = result['checksum']
        total_records = result['total_records']
        preview_data = result['preview_data']
        report_obj = result.get('report_obj')

        return Response({
            'report_id': report_obj.id if report_obj else None,
            'total_records': total_records,
            'preview_data': preview_data,
            'filename': filename,
            'checksum': checksum
        })


class ReportDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsAdvancedUser]

    def get(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)

        try:
            file_handle = report.file.open('rb')
            response = FileResponse(file_handle, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{report.file.name.split("/")[-1]}"'
            return response
        except FileNotFoundError:
            raise Http404("File not found")
 

class ReportIssueCreateView(generics.CreateAPIView):
    queryset = ReportIssue.objects.all()
    serializer_class = ReportIssueCreateSerializer
    permission_classes = [IsAuthenticated, IsAdvancedUser]

    def perform_create(self, serializer):
        report_id = self.kwargs.get('report_id')
        report = Report.objects.get(id=report_id)

        serializer.save(
            report=report,
            user=self.request.user.advanced_profile
        )