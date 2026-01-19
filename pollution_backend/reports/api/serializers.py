from rest_framework import serializers

class DataExportRequestSerializer(serializers.Serializer):
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        # ('pdf', 'PDF'),
        ]
    
    date_from = serializers.DateField(required=True)
    date_to = serializers.DateField(required=True)

    station_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        allow_empty=True
    )

    pollutant_symbols = serializers.ListField(
        child=serializers.CharField(), 
        required=False, 
        allow_empty=True
    )

    file_format = serializers.ChoiceField(choices=FORMAT_CHOICES, required=True)

    def validate(self, data):
        if data['date_from'] > data['date_to']:
            raise serializers.ValidationError("date_from cannot be later than date_to.")
        return data