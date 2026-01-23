from django.urls import re_path

from pollution_backend.realtime.consumers import DeviceStatusConsumer

websocket_urlpatterns = [
    re_path(r"ws/sensor/(?P<sensor_id>\d+)/status/$", DeviceStatusConsumer.as_asgi()),
    re_path(r"ws/station/(?P<station_id>\d+)/status/$", DeviceStatusConsumer.as_asgi()),
]
