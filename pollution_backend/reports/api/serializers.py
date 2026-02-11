from rest_framework import serializers
from pollution_backend.reports.models import Report, ReportIssue


class ReportSerializer(serializers.ModelSerializer):
    author_email = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'title', 'created_at', 'file', 'parameters', 'results', 'author_email']
        read_only_fields = ['created_at', 'author_email']

    def get_author_email(self, obj):
        if obj.advanced_user and obj.advanced_user.user:
            return obj.advanced_user.user.email
        return None


class ReportCreateFromAnalysisSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    analysis_type = serializers.ChoiceField(choices=[
        ('descriptive', 'Statystyki opisowe'),
        ('trend', 'Analiza trendów'),
        ('comparison', 'Porównanie okresów'),
        ('exceedance', 'Przekroczenia norm'),
    ])
    sensor_id = serializers.IntegerField()
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    sensor_info = serializers.DictField(required=False, default=dict)
    results = serializers.DictField()
    selected_elements = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    output_format = serializers.ChoiceField(choices=[('pdf', 'PDF'), ('html', 'HTML')], default='pdf')


class DataExportRequestSerializer(serializers.Serializer):
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('pdf', 'PDF'),
    ]

    date_from = serializers.DateField(required=True)
    date_to = serializers.DateField(required=True)
    station_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    pollutant_symbols = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    file_format = serializers.ChoiceField(choices=FORMAT_CHOICES, required=True)

    def validate(self, data):
        if data['date_from'] > data['date_to']:
            raise serializers.ValidationError("date_from cannot be later than date_to.")
        return data


class ReportIssueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportIssue
        fields = ['description']
