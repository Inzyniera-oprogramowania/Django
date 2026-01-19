from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.models import Sensor
import json
import io
import hashlib
import csv
from xml.etree.ElementTree import Element, SubElement, tostring
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


class ExportService:
    def __init__(self, validate_data):
        self.data = validate_data
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
            time__range = (self.data['date_from'], self.data['date_to']),
            sensor_id__in=target_sensor_ids
        ).order_by('time')
  

        return queryset
    
    def generate_file(self):
        file_format = self.data['file_format']

        measurements = []

        for measurement in self.queryset:
            metadata = self.sensor_map.get(measurement.sensor_id)
            measurements.append({
                    "time": measurement.time.isoformat(),
                    "value": measurement.value,
                    "unit": measurement.unit,
                    "station": metadata['station'],     
                    "pollutant": metadata['pollutant']  
                })

        if not measurements:
            return None
        
        content = ""
        content_type = ""

        if file_format == 'csv':
            content, content_type = self._generate_csv(measurements)
        elif file_format == 'json':
            content, content_type = self._generate_json(measurements)
        elif file_format == 'xml':
            content, content_type = self._generate_xml(measurements)
        elif file_format == 'pdf':
            content, content_type = self._generate_pdf(measurements)
        else:
            raise ValueError("Unsupported file format")
        
        if isinstance(content, str):
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        else:
            checksum = hashlib.sha256(content).hexdigest()
        date_from_str = self.data['date_from'].strftime('%Y-%m-%d')
        date_to_str = self.data['date_to'].strftime('%Y-%m-%d')
        
        filename = f"export_{date_from_str}_{date_to_str}.{file_format}"

        return content, content_type, filename, checksum

    def _generate_csv(self, measurements):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=measurements[0].keys())
        writer.writeheader()
        writer.writerows(measurements)
        content = output.getvalue()
        content_type = "text/csv"
        return content, content_type
    
    def _generate_json(self, measurements):
        content = json.dumps(measurements, indent=4, ensure_ascii=False)
        content_type = "application/json"
        return content, content_type

    def _generate_xml(self, measurements):
        root = Element("measurements")
        for measurement in measurements:
            item = SubElement(root, "measurement")
            for key, val in measurement.items():
                child = SubElement(item, key)
                child.text = str(val)

        content = tostring(root, encoding="unicode")
        content_type = "application/xml"
        return content, content_type

    def _generate_pdf(self, measurements):
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        title = f"Measurement Export from {self.data['date_from']} to {self.data['date_to']}"
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Paragraph("<br/><br/>", styles['Normal']))

        data = [['Time', 'Value', 'Unit', 'Station', 'Pollutant']] 

        for m in measurements:
            data.append([m['time'], str(m['value']), m['unit'], m['station'], m['pollutant']])

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),       
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),              
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),    
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),             
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),     
            ('GRID', (0, 0), (-1, -1), 1, colors.black),        
        ]))

        elements.append(table)

        doc.build(elements)

        pdf_value = buffer.getvalue()
        buffer.close()

        return pdf_value.decode('latin1'), "application/pdf"