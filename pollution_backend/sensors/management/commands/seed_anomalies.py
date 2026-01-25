"""
Management command to seed test anomaly data.
Usage: python manage.py seed_anomalies
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from pollution_backend.sensors.models import AnomalyLog, Sensor


class Command(BaseCommand):
    help = "Seed the database with test anomaly data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of anomalies to create (default: 10)",
        )

    def handle(self, *args, **options):
        count = options["count"]
        
        # Get the first active sensor
        sensor = Sensor.objects.filter(is_active=True).first()
        if not sensor:
            self.stdout.write(self.style.ERROR("No active sensors found!"))
            return

        statuses = ["pending", "confirmed", "dismissed"]
        descriptions = [
            "Nagły wzrost PM10 - przekroczony próg bezpieczeństwa",
            "Wartość PM2.5 znacznie powyżej normy dziennej",
            "Outlier - nierealistycznie wysoki odczyt NO2",
            "Brak danych przez 30 minut - możliwa awaria czujnika",
            "Przekroczenie normy godzinowej O3",
            "Nagły spadek wartości - możliwa kalibracja",
            "Wartość ujemna - błąd pomiaru",
            "Przekroczenie alertu WHO dla PM10",
        ]

        now = timezone.now()
        created_count = 0

        for i in range(count):
            anomaly = AnomalyLog.objects.create(
                description=descriptions[i % len(descriptions)],
                detected_at=now - timedelta(hours=i * 2, minutes=i * 15),
                status=statuses[i % len(statuses)],
                sensor=sensor,
            )
            created_count += 1
            self.stdout.write(f"Created anomaly #{anomaly.id}: {anomaly.description[:40]}...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} anomalies for sensor #{sensor.id}")
        )
