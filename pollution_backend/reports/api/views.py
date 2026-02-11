import os
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
from drf_spectacular.utils import extend_schema
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings

from pollution_backend.users.api.permissions import IsAdvancedUser
from pollution_backend.reports.models import Report, ReportIssue
from pollution_backend.reports.api.serializers import (
    DataExportRequestSerializer,
    ReportIssueCreateSerializer,
    ReportSerializer,
    ReportCreateFromAnalysisSerializer,
)
from pollution_backend.services.analysis_report import AnalysisReportGenerator
from pollution_backend.services.reports import ExportService


class ReportViewSet(ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return Report.objects.select_related('advanced_user__user').all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'download']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdvancedUser()]

    @extend_schema(request=ReportCreateFromAnalysisSerializer, responses={201: ReportSerializer})
    def create(self, request, *args, **kwargs):
        serializer = ReportCreateFromAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            generator = AnalysisReportGenerator(data=serializer.validated_data, user=request.user)
            report = generator.save_to_report()

            return Response({
                'id': report.id,
                'title': report.title,
                'file': report.file,
                'download_url': f'/api/reports/{report.id}/download/',
                'message': 'Raport wygenerowany'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='my')
    def my_reports(self, request):
        if not hasattr(request.user, 'advanced_profile'):
            return Response([])
        queryset = self.get_queryset().filter(advanced_user=request.user.advanced_profile)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        report = self.get_object()
        if not report.file:
            raise Http404("Brak pliku")

        return FileResponse(report.file.open('rb'), content_type='application/pdf',
                          as_attachment=True, filename=os.path.basename(report.file.name))


class MeasurementExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdvancedUser]

    @extend_schema(request=DataExportRequestSerializer)
    def post(self, request):
        serializer = DataExportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        service = ExportService(serializer.validated_data, user=request.user)
        result = service.execute_and_save()

        if result is None:
            return Response({"detail": "Brak danych"}, status=status.HTTP_404_NOT_FOUND)

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
        if not report.file:
            raise Http404("Brak pliku")

        return FileResponse(report.file.open('rb'), content_type='application/pdf',
                          as_attachment=True, filename=os.path.basename(report.file.name))


class ReportIssueCreateView(generics.CreateAPIView):
    queryset = ReportIssue.objects.all()
    serializer_class = ReportIssueCreateSerializer
    permission_classes = [IsAuthenticated, IsAdvancedUser]

    def perform_create(self, serializer):
        report = Report.objects.get(id=self.kwargs.get('report_id'))
        serializer.save(report=report, user=self.request.user.advanced_profile)
