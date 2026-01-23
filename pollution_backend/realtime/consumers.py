import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class DeviceStatusConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.sensor_id = self.scope["url_route"]["kwargs"].get("sensor_id")
        self.station_id = self.scope["url_route"]["kwargs"].get("station_id")
        
        if self.sensor_id:
            self.device_id = int(self.sensor_id)
            self.device_type = "sensor"
            self.group_name = f"sensor_{self.device_id}_status"
        elif self.station_id:
            self.device_id = int(self.station_id)
            self.device_type = "station"
            self.group_name = f"station_{self.device_id}_status"
        else:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info("WebSocket connected: %s_id=%s", self.device_type, self.device_id)

        if self.device_type == "sensor":
            try:
                measurements = await self.get_latest_measurements(self.device_id, 5)
                for m in reversed(measurements):
                    await self.send_json({
                        "msg_type": "measurement",
                        "sensor_id": self.device_id,
                        "value": m.value,
                        "unit": m.unit,
                        "timestamp": m.time.isoformat(),
                    })
            except Exception as e:
                logger.error("Failed to fetch/send initial measurements: %s", e)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info("WebSocket disconnected: sensor_id=%s, code=%s", self.sensor_id, close_code)

    async def status_update(self, event):
        await self.send_json(event["data"])

    async def system_log(self, event):
        await self.send_json(event["data"])

    async def measurement(self, event):
        await self.send_json(event["data"])

    from channels.db import database_sync_to_async
    @database_sync_to_async
    def get_latest_measurements(self, sensor_id, limit=5):
        from pollution_backend.measurements.models import Measurement
        qs = Measurement.objects.using("timeseries").filter(sensor_id=sensor_id).order_by("-time")[:limit]
        return list(qs)
