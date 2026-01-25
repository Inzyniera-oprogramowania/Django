
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.models import Sensor

class Command(BaseCommand):
    help = "Seed historical measurement data for all sensors"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of days of history to generate (default: 90)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        sensors = Sensor.objects.filter(is_active=True)
        
        if not sensors.exists():
            self.stdout.write(self.style.ERROR("No active sensors found!"))
            return

        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        
        total_created = 0
        
        for sensor in sensors:
            self.stdout.write(f"Seeding data for sensor: {sensor}")
            
            # Determine base value based on pollutant
            base_value = 20.0
            if sensor.pollutant:
                symbol = sensor.pollutant.symbol
                if symbol == "PM25": base_value = 25.0
                elif symbol == "PM10": base_value = 40.0
                elif symbol == "NO2": base_value = 30.0
                elif symbol == "O3": base_value = 60.0
                elif symbol == "SO2": base_value = 10.0
                elif symbol == "CO": base_value = 1000.0 # CO is usually higher in μg/m3 or distinct unit

            measurements = []
            current_time = start_time
            
            # Generate hourly data
            while current_time <= end_time:
                # Add some randomness and daily cycle
                hour_factor = 1.5 if 7 <= current_time.hour <= 20 else 0.5 # Higher during day
                random_variation = random.uniform(0.5, 1.5)
                
                value = base_value * hour_factor * random_variation
                
                measurements.append(Measurement(
                    time=current_time,
                    sensor_id=sensor.id,
                    value=round(value, 2),
                    unit="µg/m³" # Default unit
                ))
                
                current_time += timedelta(hours=1)
                
            # Bulk create for performance
            Measurement.objects.bulk_create(measurements, ignore_conflicts=True)
            count = len(measurements)
            total_created += count
            self.stdout.write(f"  - Created {count} measurements")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {total_created} measurements across {sensors.count()} sensors."))
