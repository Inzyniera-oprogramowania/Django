from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.models import Sensor
from pollution_backend.reports.models import Report
from django.core.files.base import ContentFile
import traceback
import json
import io
import hashlib
import csv
from xml.etree.ElementTree import Element, SubElement, tostring
from itertools import groupby
from operator import itemgetter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class ExportService:
    def __init__(self, validate_data, user):
        self.data = validate_data
        self.user = user
        self.sensor_map = self._get_sensor_metadata()
        self.queryset = self._get_measurements()

    def _get_sensor_metadata(self):
        sensors = Sensor.objects.all().select_related('monitoring_station', 'pollutant')

        if self.data.get('station_ids'):
            sensors = sensors.filter(monitoring_station_id__in=self.data['station_ids'])
        
        if self.data.get('pollutant_symbols'):
            sensors = sensors.filter(pollutant__symbol__in=self.data['pollutant_symbols'])

        sensor_map = {}
        for s in sensors:
            sensor_map[s.id] = {
                'station': s.monitoring_station.station_code,
                'pollutant': s.pollutant.symbol
            }
        return sensor_map

    def _get_measurements(self):
        if not self.sensor_map:
            return Measurement.objects.none()

        target_sensor_ids = list(self.sensor_map.keys())
        
        queryset = Measurement.objects.filter(
            time__range=(self.data['date_from'], self.data['date_to']),
            sensor_id__in=target_sensor_ids
        )

        return queryset
    
    def generate_file(self):
        file_format = self.data['file_format']
        measurements_data = []

        for measurement in self.queryset:
            metadata = self.sensor_map.get(measurement.sensor_id)
            
            if not metadata:
                continue

            measurements_data.append({
                "time_obj": measurement.time,
                "time": measurement.time.isoformat(),
                "display_time": measurement.time.strftime("%Y-%m-%d %H:%M"),
                "value": measurement.value,
                "unit": measurement.unit,
                "station": metadata['station'],     
                "pollutant": metadata['pollutant']  
            })

        if not measurements_data:
            return None

        measurements_data.sort(key=itemgetter('station', 'pollutant', 'time_obj'))
        
        content = ""
        content_type = ""

        if file_format == 'csv':
            content, content_type = self._generate_csv(measurements_data)
        elif file_format == 'json':
            content, content_type = self._generate_json(measurements_data)
        elif file_format == 'xml':
            content, content_type = self._generate_xml(measurements_data)
        elif file_format == 'pdf':
            content, content_type = self._generate_pdf(measurements_data)
        else:
            raise ValueError("Unsupported file format")
        
        if isinstance(content, str):
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        else:
            checksum = hashlib.sha256(content).hexdigest()

        date_from_str = self.data['date_from'].strftime('%Y-%m-%d')
        date_to_str = self.data['date_to'].strftime('%Y-%m-%d')
        
        filename = f"export_{date_from_str}_{date_to_str}.{file_format}"

        total_records = len(measurements_data)
        preview_data = [{k: v for k, v in m.items() if k != 'time_obj'} for m in measurements_data[:5]]

        return content, content_type, filename, checksum, total_records, preview_data

    def execute_and_save(self):
        result = self.generate_file()
        
        if result is None:
            return None

        content, content_type, filename, checksum, total_records, preview_data = result

        if isinstance(content, str):
            file_content = ContentFile(content.encode('utf-8'))
        else:
            file_content = ContentFile(content)

        try:
            if hasattr(self.user, 'advanced_profile'):
                adv_user = self.user.advanced_profile
            else:
                adv_user = None 

            report_params = self.data.copy()
            if 'date_from' in report_params:
                report_params['date_from'] = report_params['date_from'].strftime('%Y-%m-%d')
            if 'date_to' in report_params:
                report_params['date_to'] = report_params['date_to'].strftime('%Y-%m-%d')

            report = None
            if adv_user:
                report = Report.objects.create(
                    title=f"Export {self.data['file_format'].upper()} - {filename}",
                    advanced_user=adv_user,
                    parameters=report_params
                )
                report.file.save(filename, file_content)
                report.save()

        except Exception as e:
            print(f"ERROR: Database save failed: {e}")
            traceback.print_exc()
            report = None
        
        return {
            "report_obj": report,
            "content": content,
            "content_type": content_type,
            "filename": filename,
            "checksum": checksum,
            "total_records": total_records,
            "preview_data": preview_data
        }

    def _generate_csv(self, measurements):
        output = io.StringIO()
        fieldnames = ['time', 'value', 'unit', 'station', 'pollutant']
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(measurements)
        content = output.getvalue()
        return content, "text/csv"
    
    def _generate_json(self, measurements):
        clean_data = [{k: v for k, v in m.items() if k not in ['display_time', 'time_obj']} for m in measurements]
        content = json.dumps(clean_data, indent=4, ensure_ascii=False)
        return content, "application/json"

    def _generate_xml(self, measurements):
        root = Element("measurements")
        for measurement in measurements:
            item = SubElement(root, "measurement")
            for key in ['time', 'value', 'unit', 'station', 'pollutant']:
                child = SubElement(item, key)
                child.text = str(measurement.get(key, ''))

        content = tostring(root, encoding="unicode")
        return content, "application/xml"

    def _generate_pdf(self, measurements):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        elements = []
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            alignment=TA_CENTER,
            spaceAfter=30,
            fontSize=18,
            textColor=colors.black
        )
        
        station_header_style = ParagraphStyle(
            'StationHeader',
            parent=styles['Heading2'],
            alignment=TA_LEFT,
            spaceBefore=15,
            spaceAfter=10,
            fontSize=14,
            textColor=colors.black,
            borderPadding=5,
        )

        pollutant_header_style = ParagraphStyle(
            'PollutantHeader',
            parent=styles['Heading3'],
            alignment=TA_LEFT,
            spaceBefore=10,
            spaceAfter=5,
            fontSize=12,
            textColor=colors.dimgray,
            fontName='Helvetica-Oblique'
        )

        date_from = self.data['date_from'].strftime('%Y-%m-%d')
        date_to = self.data['date_to'].strftime('%Y-%m-%d')
        elements.append(Paragraph(f"Raport Pomiarów", title_style))
        elements.append(Paragraph(f"Okres: {date_from} do {date_to}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        for station_code, station_group in groupby(measurements, key=itemgetter('station')):
            elements.append(Paragraph(f"Stacja: {station_code}", station_header_style))
            
            station_data = list(station_group)
            
            for pollutant_symbol, pollutant_group in groupby(station_data, key=itemgetter('pollutant')):
                elements.append(Paragraph(f"Zanieczyszczenie: {pollutant_symbol}", pollutant_header_style))
                
                table_data = [['Czas', 'Wartosc', 'Jednostka']] 
                
                for m in pollutant_group:
                    val_str = f"{m['value']:.2f}" if isinstance(m['value'], float) else str(m['value'])
                    table_data.append([m['display_time'], val_str, m['unit']])
                
                t = Table(table_data, colWidths=[200, 100, 100])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ]))
                
                elements.append(t)
                elements.append(Spacer(1, 15))
            
            elements.append(Spacer(1, 20))

        doc.build(elements)
        pdf_value = buffer.getvalue()
        buffer.close()

        return pdf_value, "application/pdf"