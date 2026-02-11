import factory
from factory.django import DjangoModelFactory
from django.contrib.gis.geos import Point
from pollution_backend.sensors.models import (
    Pollutant,
    Location,
    MonitoringStation,
    Sensor,
    DeviceStatus,
    AnomalyRule,
)

class PollutantFactory(DjangoModelFactory):
    class Meta:
        model = Pollutant
        django_get_or_create = ["symbol"]

    name = factory.LazyAttribute(lambda obj: f"Pollutant_{obj.symbol}")
    symbol = factory.Sequence(lambda n: f"POL_{n}")
    description = factory.Faker("sentence")


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    geom = Point(17.04, 51.11)
    altitude = factory.Faker("random_int", min=200, max=300)
    full_address = factory.Faker("address")
    h3_index = factory.Faker("bothify", text="?????")


class MonitoringStationFactory(DjangoModelFactory):
    class Meta:
        model = MonitoringStation
        django_get_or_create = ["station_code"]

    station_code = factory.Sequence(lambda n: f"ST_{n}")
    owner = factory.Faker("company")
    launch_date = factory.Faker("date_object")
    is_active = True
    location = factory.SubFactory(LocationFactory)


class SensorFactory(DjangoModelFactory):
    class Meta:
        model = Sensor
        django_get_or_create = ["serial_number"]

    sensor_type = "PM10"
    manufacturer = factory.Faker("company")
    serial_number = factory.Sequence(lambda n: f"SN_{n}")
    is_active = True
    monitoring_station = factory.SubFactory(MonitoringStationFactory)
    pollutant = factory.SubFactory(PollutantFactory)


class DeviceStatusFactory(DjangoModelFactory):
    class Meta:
        model = DeviceStatus

    sensor = factory.SubFactory(SensorFactory)
    battery_percent = factory.Faker("random_int", min=0, max=100)
    signal_rssi_dbm = factory.Faker("random_int", min=-100, max=-30)
    uptime_seconds = factory.Faker("random_int", min=0, max=100000)


class AnomalyRuleFactory(DjangoModelFactory):
    class Meta:
        model = AnomalyRule

    pollutant = factory.SubFactory(PollutantFactory)
    is_enabled = True
    warning_threshold = 50.0
    critical_threshold = 100.0
    sudden_change_enabled = True
