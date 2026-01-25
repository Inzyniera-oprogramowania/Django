"""
MQTT Client for Real-time Sensor Data Ingestion.

This module provides an MQTT client that subscribes to sensor data topics,
parses incoming JSON messages, and stores measurements in the database.
It also triggers anomaly detection for each received measurement.
"""

import json
import logging
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone

from pollution_backend.measurements.models import Measurement
from pollution_backend.sensors.models import Sensor

logger = logging.getLogger(__name__)


class MQTTClient:
    """
    MQTT Client for subscribing to sensor data and processing measurements.

    This client connects to an MQTT broker, subscribes to sensor topics,
    and processes incoming measurement data according to the format:

    Topic: sensors/{station_code}/{pollutant_symbol}
    Payload: {
        "sensor_id": int,
        "value": float,
        "unit": str,
        "timestamp": str (ISO 8601)
    }

    Attributes:
        broker_host: MQTT broker hostname
        broker_port: MQTT broker port
        topics: List of topic patterns to subscribe to
        client: paho-mqtt client instance
    """

    def __init__(
        self,
        broker_host: str | None = None,
        broker_port: int | None = None,
        topics: list[str] | None = None,
        client_id: str | None = None,
    ) -> None:
        """
        Initialize the MQTT client.

        Args:
            broker_host: MQTT broker hostname. Defaults to settings.MQTT_BROKER_HOST
            broker_port: MQTT broker port. Defaults to settings.MQTT_BROKER_PORT
            topics: List of topic patterns. Defaults to settings.MQTT_TOPICS
            client_id: Optional client ID for MQTT connection
        """
        self.broker_host = broker_host or getattr(settings, "MQTT_BROKER_HOST", "mosquitto")
        self.broker_port = broker_port or getattr(settings, "MQTT_BROKER_PORT", 1883)
        self.topics = topics or getattr(settings, "MQTT_TOPICS", ["sensors/#"])

        self.client = mqtt.Client(
            client_id=client_id or "django_mqtt_client",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        logger.info(
            "MQTTClient initialized: host=%s, port=%d, topics=%s",
            self.broker_host,
            self.broker_port,
            self.topics,
        )

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        """
        Callback when connection to broker is established.

        Subscribes to all configured topics upon successful connection.

        Args:
            client: The MQTT client instance
            userdata: User data passed to callbacks
            flags: Response flags from the broker
            reason_code: Connection result code
            properties: MQTT v5 properties (optional)
        """
        if reason_code.is_failure:
            logger.error("Failed to connect to MQTT broker: %s", reason_code)
        else:
            logger.info("Connected to MQTT broker at %s:%d", self.broker_host, self.broker_port)
            for topic in self.topics:
                client.subscribe(topic)
                logger.info("Subscribed to topic: %s", topic)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        """
        Callback when disconnected from broker.

        Args:
            client: The MQTT client instance
            userdata: User data passed to callbacks
            disconnect_flags: Disconnect flags
            reason_code: Disconnection reason code
            properties: MQTT v5 properties (optional)
        """
        logger.warning("Disconnected from MQTT broker: %s", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        """
        Callback when a message is received.

        Parses the JSON payload and routes to appropriate handler:
        - sensors/{station}/status -> device status updates
        - sensors/{station}/{pollutant} -> measurement data

        Args:
            client: The MQTT client instance
            userdata: User data passed to callbacks
            message: The received MQTT message
        """
        try:
            topic = message.topic
            payload = message.payload.decode("utf-8")
            logger.debug("Received message on topic '%s': %s", topic, payload)

            # Parse topic to extract station_code and message type
            topic_parts = topic.split("/")
            if len(topic_parts) >= 3:
                station_code = topic_parts[1]
                topic_type = topic_parts[2]

                # Parse JSON payload
                data = json.loads(payload)

                # Route to appropriate handler
                if topic_type == "status":
                    self._process_device_status(data)
                elif topic_type == "heartbeat":
                    self._process_station_heartbeat(station_code, data)
                else:
                    # Existing measurement processing
                    logger.debug(
                        "Parsed topic: station_code=%s, pollutant_symbol=%s",
                        station_code,
                        topic_type,
                    )
                    self._process_measurement(data)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON payload: %s", e)
        except Exception as e:
            logger.exception("Error processing MQTT message: %s", e)

    def _process_measurement(self, data: dict[str, Any]) -> None:
        """
        Process and save a measurement from MQTT data.

        Args:
            data: Dictionary containing measurement data with keys:
                - sensor_id: int
                - value: float
                - unit: str
                - timestamp: str (ISO 8601 format)
        """
        try:
            sensor_id = data.get("sensor_id")
            value = data.get("value")
            unit = data.get("unit", "µg/m³")
            timestamp_str = data.get("timestamp")

            if not all([sensor_id, value is not None, timestamp_str]):
                logger.error("Missing required fields in measurement data: %s", data)
                return

            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if timezone.is_naive(timestamp):
                timestamp = timezone.make_aware(timestamp)

            # Validate sensor exists
            try:
                sensor = Sensor.objects.get(id=sensor_id)
            except Sensor.DoesNotExist:
                logger.warning("Sensor with ID %d not found, skipping measurement", sensor_id)
                return

            # Save measurement using the timeseries database
            measurement = Measurement(
                time=timestamp,
                sensor_id=sensor_id,
                value=value,
                unit=unit,
            )
            measurement.save(using="timeseries")

            logger.info(
                "Saved measurement: sensor_id=%d, value=%.2f %s, time=%s",
                sensor_id,
                value,
                unit,
                timestamp,
            )

            # Trigger anomaly detection task
            from pollution_backend.realtime.tasks import check_anomaly

            check_anomaly.delay(sensor_id=sensor_id, value=value, timestamp=timestamp_str)

            # Broadcast measurement via WebSocket
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"sensor_{sensor_id}_status",
                    {
                        "type": "measurement",
                        "data": {
                            "msg_type": "measurement",
                            "sensor_id": sensor_id,
                            "value": value,
                            "unit": unit,
                            "timestamp": timestamp.isoformat(),
                        },
                    },
                )

        except Exception as e:
            logger.exception("Failed to process measurement: %s", e)

    def _process_device_status(self, data: dict[str, Any]) -> None:
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            from pollution_backend.sensors.models import DeviceStatus
            from pollution_backend.sensors.models import Sensor

            sensor_id = data.get("sensor_id")
            if not sensor_id:
                logger.error("Missing sensor_id in device status data: %s", data)
                return

            print(f"DEBUG: Processing device status for sensor {sensor_id}: {data}", flush=True)

            # Validate sensor exists
            try:
                sensor = Sensor.objects.get(id=sensor_id)
            except Sensor.DoesNotExist:
                logger.warning("Sensor with ID %d not found, skipping status update", sensor_id)
                return

            # Retrieve data
            battery = data.get("battery_percent", 100)
            rssi = data.get("signal_rssi_dbm", -50)
            uptime = data.get("uptime_seconds", 0)

            # Handle 0% battery -> deactivate sensor
            if battery == 0 and sensor.is_active:
                sensor.is_active = False
                sensor.save()
                logger.warning("Sensor %s disabled due to empty battery", sensor_id)
                try:
                    from pollution_backend.measurements.models import SystemLog
                    SystemLog.objects.create(
                        event_type="BATTERY_CRITICAL",
                        message=f"Sensor {sensor_id} disabled due to empty battery (0%)",
                        log_level=SystemLog.WARNING,
                        sensor_id=sensor_id,
                    )
                except Exception as e:
                    logger.error("Failed to create SystemLog for battery: %s", e)
            
            # Log periodic status update to SystemLog (as requested by user)
            try:
                from pollution_backend.measurements.models import SystemLog
                SystemLog.objects.create(
                    event_type="DEVICE_STATUS",
                    message=f"Status update: Battery {battery}%, Signal {rssi}dBm, Uptime {uptime}s",
                    log_level=SystemLog.INFO,
                    sensor_id=sensor_id,
                )
            except Exception as e:
                logger.error("Failed to create SystemLog: %s", e)

            # Update or create DeviceStatus record
            status, created = DeviceStatus.objects.update_or_create(
                sensor_id=sensor_id,
                defaults={
                    "battery_percent": battery,
                    "signal_rssi_dbm": rssi,
                    "uptime_seconds": uptime,
                },
            )

            action = "Created" if created else "Updated"
            logger.info(
                "%s device status: sensor_id=%d, battery=%d%%, rssi=%d dBm, uptime=%ds",
                action,
                sensor_id,
                status.battery_percent,
                status.signal_rssi_dbm,
                status.uptime_seconds,
            )

            # Broadcast to WebSocket group
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"sensor_{sensor_id}_status",
                    {
                        "type": "status_update",
                        "data": {
                            "msg_type": "status",
                            "sensor_id": sensor_id,
                            "battery_percent": status.battery_percent,
                            "signal_rssi_dbm": status.signal_rssi_dbm,
                            "uptime_seconds": status.uptime_seconds,
                            "updated_at": status.updated_at.isoformat(),
                        },
                    },
                )

        except Exception as e:
            logger.exception("Failed to process device status: %s", e)

    def connect(self) -> None:
        """
        Connect to the MQTT broker.

        Raises:
            ConnectionError: If connection to the broker fails
        """
        try:
            logger.info("Connecting to MQTT broker at %s:%d...", self.broker_host, self.broker_port)
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %s", e)
            raise ConnectionError(f"Could not connect to MQTT broker: {e}") from e

    def start(self) -> None:
        """
        Start the MQTT client loop.

        This is a blocking call that processes network traffic and
        dispatches callbacks. Use for running as a standalone process.
        """
        self.connect()
        logger.info("Starting MQTT client loop...")
        self.client.loop_forever()

    def _process_station_heartbeat(self, station_code: str, data: dict[str, Any]) -> None:
        try:
            from pollution_backend.sensors.models import MonitoringStation
            from pollution_backend.measurements.models import SystemLog
            from pollution_backend.sensors.api.views import broadcast_station_log

            try:
                station = MonitoringStation.objects.get(station_code=station_code)
            except MonitoringStation.DoesNotExist:
                logger.warning("Station %s not found for heartbeat", station_code)
                return

            timestamp = timezone.now()
            
            log = SystemLog.objects.create(
                station_id=station.id,
                event_type="STATION_HEARTBEAT",
                message=f"Station {station_code} is online (Heartbeat)",
                log_level=SystemLog.INFO
            )
            
            # Broadcast
            broadcast_station_log(station.id, log)
            logger.info("Processed heartbeat for station %s", station_code)

        except Exception as e:
            logger.exception("Failed to process station heartbeat: %s", e)

    def stop(self) -> None:
        """
        Stop the MQTT client and disconnect from the broker.
        """
        logger.info("Stopping MQTT client...")
        self.client.disconnect()
        self.client.loop_stop()
