import re
import time
import requests
from django.contrib.gis.geos import Point
from pollution_backend.sensors.models import MonitoringStation, Location
from pollution_backend.services.redis_cache import DeviceListCache

class StationService:
    @staticmethod
    def geocode_address(address):
        geocode_url = "https://nominatim.openstreetmap.org/search"
        
        def clean_addr(a):
            val = re.sub(r'^(ul\.|al\.|os\.|pl\.)\s*', '', a, flags=re.IGNORECASE)
            val = re.sub(r'/\d+[a-zA-Z]*', '', val)
            return val.strip()

        attempts = sorted(list(set([address, clean_addr(address)])), key=len, reverse=True)
        
        for attempt in attempts:
            try:
                ua = f"PollutionApp_DEV_{int(time.time())}"
                resp = requests.get(geocode_url, params={
                    "q": attempt, "format": "json", "limit": 1
                }, headers={"User-Agent": ua}, timeout=10)
                
                if resp.status_code == 200 and resp.json():
                    result = resp.json()[0]
                    return {
                        "lat": float(result["lat"]),
                        "lon": float(result["lon"]),
                        "display_name": result.get("display_name")
                    }
            except Exception:
                continue
        return None

    @staticmethod
    def create_station(validated_data):
        address = validated_data['address']
        geo_data = {
            "lat": 52.2297, "lon": 21.0122, "display_name": address
        }
        
        found_geo = StationService.geocode_address(address)
        if found_geo:
            geo_data = found_geo
            
        location = Location.objects.create(
            geom=Point(geo_data['lon'], geo_data['lat'], srid=4326),
            full_address=geo_data['display_name']
        )
        
        station = MonitoringStation.objects.create(
            station_code=validated_data['station_code'],
            owner=validated_data.get('owner') or None,
            location=location,
            is_active=True
        )
        
        DeviceListCache.invalidate()
        return station, geo_data