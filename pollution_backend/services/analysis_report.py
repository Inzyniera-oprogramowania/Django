import io
import os
from datetime import datetime

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pollution_backend.reports.models import Report

FONT_DIR = os.path.join(settings.BASE_DIR, 'pollution_backend', 'static', 'fonts')

try:
    pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(FONT_DIR, 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')))
    DEFAULT_FONT = 'DejaVu'
    BOLD_FONT = 'DejaVu-Bold'
except:
    DEFAULT_FONT = 'Helvetica'
    BOLD_FONT = 'Helvetica-Bold'


class AnalysisReportGenerator:
    ANALYSIS_TYPE_LABELS = {
        'descriptive': 'Statystyki opisowe',
        'trend': 'Analiza trendów',
        'comparison': 'Porównanie okresów',
        'exceedance': 'Przekroczenia norm',
    }

    def __init__(self, data: dict, user):
        self.data = data
        self.user = user
        self.styles = self._create_styles()

    def _create_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontName=BOLD_FONT, fontSize=18, alignment=TA_CENTER, spaceAfter=20))
        styles.add(ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontName=BOLD_FONT, fontSize=14, spaceBefore=15, spaceAfter=10))
        styles.add(ParagraphStyle('CustomBody', parent=styles['Normal'], fontName=DEFAULT_FONT, fontSize=10, spaceBefore=6, spaceAfter=6))
        styles.add(ParagraphStyle('CustomFooter', parent=styles['Normal'], fontName=DEFAULT_FONT, fontSize=8, alignment=TA_CENTER, textColor=colors.gray))
        return styles

    def generate(self) -> tuple[bytes, str]:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []

        elements.append(Paragraph(self.data.get('title', 'Raport'), self.styles['CustomTitle']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
        elements.append(Spacer(1, 10))

        analysis_type = self.data.get('analysis_type', '')
        date_from = self.data.get('date_from', '')
        date_to = self.data.get('date_to', '')
        if hasattr(date_from, 'strftime'):
            date_from = date_from.strftime('%Y-%m-%d')
        if hasattr(date_to, 'strftime'):
            date_to = date_to.strftime('%Y-%m-%d')

        meta = [
            ['Typ analizy:', self.ANALYSIS_TYPE_LABELS.get(analysis_type, analysis_type)],
            ['Okres:', f'{date_from} - {date_to}'],
            ['Data:', datetime.now().strftime('%Y-%m-%d %H:%M')],
        ]
        if self.user:
            meta.append(['Autor:', getattr(self.user, 'email', str(self.user))])

        table = Table(meta, colWidths=[4*cm, 12*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), BOLD_FONT),
            ('FONTNAME', (1, 0), (1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 15))

        results = self.data.get('results', {})
        if analysis_type == 'descriptive':
            elements.extend(self._descriptive(results))
        elif analysis_type == 'trend':
            elements.extend(self._trend(results))
        elif analysis_type == 'comparison':
            elements.extend(self._comparison(results))
        elif analysis_type == 'exceedance':
            elements.extend(self._exceedance(results))

        elements.append(Spacer(1, 30))
        elements.append(Paragraph("System Monitoringu Jakości Powietrza", self.styles['CustomFooter']))

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        filename = f"raport_{analysis_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return pdf, filename

    def _descriptive(self, r):
        elements = [Paragraph('Statystyki opisowe', self.styles['SectionHeader'])]
        unit = r.get('unit', 'µg/m³')
        data = [
            ['Metryka', 'Wartość'],
            ['Liczba pomiarów', str(r.get('count', 0))],
            ['Średnia', f"{r.get('mean', 0):.2f} {unit}"],
            ['Mediana', f"{r.get('median', 0):.2f} {unit}"],
            ['Min', f"{r.get('min_value', 0):.2f} {unit}"],
            ['Max', f"{r.get('max_value', 0):.2f} {unit}"],
            ['Odch. std.', f"{r.get('std_dev', 0):.2f} {unit}"],
        ]
        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(table)
        return elements

    def _trend(self, r):
        elements = [Paragraph('Analiza trendów', self.styles['SectionHeader'])]
        direction = {'increasing': 'Wzrostowy', 'decreasing': 'Spadkowy', 'stable': 'Stabilny'}.get(r.get('trend_direction', 'stable'), 'Stabilny')
        data = [
            ['Kierunek trendu', direction],
            ['Zmiana procentowa', f"{r.get('percent_change', 0):+.2f}%"],
        ]
        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.gray)]))
        elements.append(table)
        return elements

    def _comparison(self, r):
        elements = [Paragraph('Porównanie okresów', self.styles['SectionHeader'])]
        data = [
            ['', 'Okres 1', 'Okres 2'],
            ['Średnia', f"{r.get('period1_avg', 0):.2f}", f"{r.get('period2_avg', 0):.2f}"],
        ]
        table = Table(data, colWidths=[5*cm, 5*cm, 5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ]))
        elements.append(table)
        elements.append(Paragraph(f"Zmiana: {r.get('percent_diff', 0):+.2f}%", self.styles['CustomBody']))
        return elements

    def _exceedance(self, r):
        elements = [Paragraph('Przekroczenia norm', self.styles['SectionHeader'])]
        data = [
            ['Liczba pomiarów', str(r.get('total_measurements', 0))],
            ['Przekroczenia', str(r.get('exceedances_count', 0))],
            ['Procent', f"{r.get('exceedance_percent', 0):.2f}%"],
        ]
        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.gray)]))
        elements.append(table)
        return elements

    def save_to_report(self) -> Report:
        pdf_content, filename = self.generate()

        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(reports_dir, exist_ok=True)

        file_path = os.path.join(reports_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(pdf_content)

        file_url = f"/media/reports/{filename}"

        advanced_user = getattr(self.user, 'advanced_profile', None)

        report = Report(
            title=self.data.get('title', 'Raport'),
            advanced_user=advanced_user,
            file=file_url,
            parameters={
                'analysis_type': self.data.get('analysis_type'),
                'sensor_id': self.data.get('sensor_id'),
                'date_from': str(self.data.get('date_from', '')),
                'date_to': str(self.data.get('date_to', '')),
            },
            results=self.data.get('results', {})
        )
        report.save()
        return report
