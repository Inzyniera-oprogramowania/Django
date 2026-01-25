
import os
import django
from django.utils import timezone
from django.contrib.gis.geos import Point

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from pollution_backend.sensors.models import Pollutant, Location, MonitoringStation, Sensor, GlobalAnomalyConfig, AnomalyRule, QualityNorm

def run():
    print("Seeding initial data...")

    # 1. Pollutants
    pollutants_data = [
        {"name": "Particulate Matter 2.5", "symbol": "PM25", "description": "Fine particles"},
        {"name": "Particulate Matter 10", "symbol": "PM10", "description": "Coarse particles"},
        {"name": "Nitrogen Dioxide", "symbol": "NO2", "description": "Traffic pollution"},
        {"name": "Ozone", "symbol": "O3", "description": "Ground level ozone"},
        {"name": "Sulfur Dioxide", "symbol": "SO2", "description": "Industrial pollution"},
        {"name": "Carbon Monoxide", "symbol": "CO", "description": "Combustion byproduct"},
    ]
    
    pollutants = {}
    for p_data in pollutants_data:
        obj, created = Pollutant.objects.get_or_create(
            symbol=p_data["symbol"],
            defaults={"name": p_data["name"], "description": p_data["description"]}
        )
        pollutants[obj.symbol] = obj
        if created:
            print(f"Created pollutant: {obj.symbol}")

    # 2. Location (Warsaw Center)
    loc, created = Location.objects.get_or_create(
        full_address="Warsaw, Marszałkowska 1",
        defaults={
            "geom": Point(21.0122, 52.2297),
            "altitude": 100,
            "h3_index": "881e282a89fffff" # Dummy H3
        }
    )
    if created:
        print("Created location: Warsaw Center")

    # 3. Station
    station, created = MonitoringStation.objects.get_or_create(
        station_code="WAW001",
        defaults={
            "owner": "GIOŚ",
            "launch_date": timezone.now().date(),
            "location": loc,
            "is_active": True
        }
    )
    if created:
        print("Created station: WAW001")

    # 4. Sensors
    for symbol in ["PM25", "PM10", "NO2", "O3", "SO2", "CO"]:
        sensor, created = Sensor.objects.get_or_create(
            serial_number=f"SENS-{symbol}-001",
            defaults={
                "sensor_type": f"Laser {symbol}",
                "manufacturer": "AirMon",
                "model": "X-2000",
                "calibration_date": timezone.now().date(),
                "is_active": True,
                "measurement_range_max": 500,
                "send_interval_seconds": 60,
                "monitoring_station": station,
                "pollutant": pollutants[symbol]
            }
        )
        if created:
            print(f"Created sensor for {symbol}")

    # 4b. Anomaly Rules
    for symbol, pollutant in pollutants.items():
        rule, created = AnomalyRule.objects.get_or_create(
            pollutant=pollutant,
            defaults={
                "is_enabled": True,
                "warning_threshold": 50.0,
                "critical_threshold": 100.0,
                "sudden_change_enabled": True,
                "sudden_change_percent": 30.0,
                "sudden_change_minutes": 15
            }
        )
        if created:
            print(f"Created AnomalyRule for {symbol}")

    # 4c. Quality Norms (WHO/EU typical values)
    norms_data = {
        "PM25": 25.0,  # 24h mean
        "PM10": 50.0,  # 24h mean
        "NO2": 40.0,   # Annual mean
        "O3": 120.0,   # 8h mean
        "SO2": 125.0,  # 24h mean
        "CO": 10000.0, # 8h mean (10mg/m3)
    }

    for symbol, pollutant in pollutants.items():
        if symbol in norms_data:
            norm, created = QualityNorm.objects.get_or_create(
                pollutant=pollutant,
                defaults={
                    "threshold_value": norms_data[symbol],
                    "unit": "µg/m³",
                    "norm_type": "Dobowa (WHO/EU)",
                    "valid_from": timezone.now().date(),
                }
            )
            if created:
                print(f"Created QualityNorm for {symbol}")

    # 5. Global Config
    GlobalAnomalyConfig.get_config()
    print("Ensured Global Config exists.")

    print("Seeding complete.")

if __name__ == "__main__":
    run()
