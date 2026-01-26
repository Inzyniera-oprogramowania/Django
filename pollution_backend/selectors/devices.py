from django.db.models import Max
from pollution_backend.sensors.models import Sensor
from pollution_backend.measurements.models import Measurement, SystemLog
from pollution_backend.selectors.sensors import get_all_stations, get_active_sensors

def get_aggregated_device_list(filters: dict):
    device_type = filters.get("type", "station")
    search = filters.get("search", "").strip()
    id_filter = filters.get("id")
    pollutant_filter = filters.get("pollutant")
    raw_active = filters.get("is_active")
    is_active_bool = None

    if str(raw_active).lower() == 'true':
        is_active_bool = True
    elif str(raw_active).lower() == 'false':
        is_active_bool = False

    devices = []

    sensor_last_times = {}
    try:
        latest_measurements = (
            Measurement.objects.values("sensor_id").annotate(last_time=Max("time"))
        )
        sensor_last_times = {m["sensor_id"]: m["last_time"] for m in latest_measurements}
    except Exception:
        pass

    if device_type in ("station", "all"):
        stations = get_all_stations()
        
        if search:
            stations = stations.filter(station_code__icontains=search) | stations.filter(
                location__full_address__icontains=search
            )
        if id_filter:
            try:
                stations = stations.filter(id=int(id_filter))
            except ValueError:
                pass
        if pollutant_filter and pollutant_filter != "Wszystkie":
            stations = stations.filter(sensor__pollutant__symbol=pollutant_filter).distinct()
        if is_active_bool is not None:
            stations = stations.filter(is_active=is_active_bool)
            
        stations = stations.prefetch_related("sensor_set__pollutant", "location")

        station_log_last_times = {}
        try:
            station_ids = [s.id for s in stations]
            latest_logs = (
                SystemLog.objects.filter(station_id__in=station_ids)
                .values("station_id").annotate(last_time=Max("timestamp"))
            )
            station_log_last_times = {l["station_id"]: l["last_time"] for l in latest_logs}
        except Exception:
            pass

        for s in stations:
            s_sensors = s.sensor_set.all()
            pollutants = sorted(list({sensor.pollutant.symbol for sensor in s_sensors if sensor.pollutant}))
            
            max_time = station_log_last_times.get(s.id)
            last_time_str = max_time.isoformat() if max_time else "-"
            
            devices.append({
                "id": s.id,
                "station_code": s.station_code,
                "type": "Stacja",
                "pollutants": pollutants,
                "address": s.location.full_address if s.location else "Brak danych",
                "lastLogTime": last_time_str,
                "is_active": s.is_active,
            })

    if device_type in ("sensor", "all"):
        sensors = Sensor.objects.all().select_related("pollutant", "monitoring_station", "monitoring_station__location")
        
        if is_active_bool is not None:
            sensors = sensors.filter(is_active=is_active_bool)
        if pollutant_filter and pollutant_filter != "Wszystkie":
            sensors = sensors.filter(pollutant__symbol=pollutant_filter)
        if id_filter:
            try:
                sensors = sensors.filter(id=int(id_filter))
            except ValueError:
                pass
        if search:
            sensors = sensors.filter(serial_number__icontains=search) | sensors.filter(
                sensor_type__icontains=search
            ) | sensors.filter(monitoring_station__station_code__icontains=search)
        
        for s in sensors:
            last_time = sensor_last_times.get(s.id)
            last_time_str = last_time.isoformat() if last_time else "-"
            
            devices.append({
                "id": s.id,
                "serial_number": s.serial_number,
                "type": "Czujnik",
                "pollutants": [s.pollutant.symbol] if s.pollutant else [],
                "address": s.monitoring_station.station_code if s.monitoring_station else "Brak danych",
                "lastLogTime": last_time_str,
                "is_active": s.is_active,
            })

    return devices