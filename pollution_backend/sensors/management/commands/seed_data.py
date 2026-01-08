import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.gis.geos import Point
from pollution_backend.sensors.models import MonitoringStation, Sensor, Pollutant, Location
from pollution_backend.measurements.models import Measurement

class Command(BaseCommand):
    help = "Generuje przykładowe dane stacji i pomiarów do testów"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Rozpoczynam sadzenie danych...")

        # 1. Tworzymy Zanieczyszczenia
        pm25, _ = Pollutant.objects.get_or_create(
            name="Pył zawieszony PM2.5", symbol="PM2.5", description="Drobny pył"
        )
        pm10, _ = Pollutant.objects.get_or_create(
            name="Pył zawieszony PM10", symbol="PM10", description="Grubszy pył"
        )

        # 2. Tworzymy Lokalizację (np. centrum Łodzi)
        loc, _ = Location.objects.get_or_create(
            full_address="Piotrkowska 100, Łódź",
            defaults={"geom": Point(19.455983, 51.762953, srid=4326)} # Longitude, Latitude
        )

        # 3. Tworzymy Stację
        station, created = MonitoringStation.objects.get_or_create(
            station_code="LDZ-001",
            defaults={
                "owner": "Miasto Łódź",
                "location": loc,
                "launch_date": timezone.now().date(),
                "is_active": True
            }
        )
        if created:
            self.stdout.write(f"Utworzono stację: {station}")

        # 4. Tworzymy Sensory
        sensor_pm25, _ = Sensor.objects.get_or_create(
            monitoring_station=station,
            pollutant=pm25,
            defaults={"sensor_type": "Laserowy", "is_active": True}
        )
        sensor_pm10, _ = Sensor.objects.get_or_create(
            monitoring_station=station,
            pollutant=pm10,
            defaults={"sensor_type": "Laserowy", "is_active": True}
        )
        
        self.stdout.write(f"ID Sensora PM2.5: {sensor_pm25.id}")
        self.stdout.write(f"ID Sensora PM10: {sensor_pm10.id}")

        # 5. Generujemy Pomiary (TimescaleDB) - Ostatnie 7 dni, co godzinę
        self.stdout.write("⏳ Generuję historię pomiarów (to może chwilę potrwać)...")
        
        measurements = []
        now = timezone.now()
        # Generujemy 500 punktów wstecz (ok 20 dni jeśli co godzinę)
        for i in range(500):
            time_point = now - timedelta(hours=i)
            
            # Symulacja: w dzień smog mniejszy, w nocy większy + losowość
            base_val = 20 if 8 <= time_point.hour <= 18 else 50
            value = base_val + random.uniform(-10, 40)
            
            measurements.append(Measurement(
                time=time_point,
                value=max(0, value), # Żeby nie było ujemnego smogu
                unit="µg/m³",
                sensor_id=sensor_pm25.id
            ))

        # Bulk create jest dużo szybszy niż pętla save()
        Measurement.objects.bulk_create(measurements)
        
        self.stdout.write(self.style.SUCCESS(f"✅ Sukces! Dodano {len(measurements)} pomiarów."))