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
    ) -> None:
        """
        Initialize the MQTT client.

        Args:
            broker_host: MQTT broker hostname. Defaults to settings.MQTT_BROKER_HOST
            broker_port: MQTT broker port. Defaults to settings.MQTT_BROKER_PORT
            topics: List of topic patterns. Defaults to settings.MQTT_TOPICS
        """
        self.broker_host = broker_host or getattr(settings, "MQTT_BROKER_HOST", "mosquitto")
        self.broker_port = broker_port or getattr(settings, "MQTT_BROKER_PORT", 1883)
        self.topics = topics or getattr(settings, "MQTT_TOPICS", ["sensors/#"])

        self.client = mqtt.Client(
            client_id="django_mqtt_client",
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

        Parses the JSON payload and saves the measurement to the database.
        Also triggers anomaly detection via Celery task.

        Args:
            client: The MQTT client instance
            userdata: User data passed to callbacks
            message: The received MQTT message
        """
        try:
            topic = message.topic
            payload = message.payload.decode("utf-8")
            logger.debug("Received message on topic '%s': %s", topic, payload)

            # Parse topic to extract station_code and pollutant_symbol
            topic_parts = topic.split("/")
            if len(topic_parts) >= 3:
                station_code = topic_parts[1]
                pollutant_symbol = topic_parts[2]
                logger.debug(
                    "Parsed topic: station_code=%s, pollutant_symbol=%s",
                    station_code,
                    pollutant_symbol,
                )

            # Parse JSON payload
            data = json.loads(payload)
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

        except Exception as e:
            logger.exception("Failed to process measurement: %s", e)

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

    def stop(self) -> None:
        """
        Stop the MQTT client and disconnect from the broker.
        """
        logger.info("Stopping MQTT client...")
        self.client.disconnect()
        self.client.loop_stop()
