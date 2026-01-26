import json
import logging
from typing import Any
import paho.mqtt.client as mqtt
from django.conf import settings
from pollution_backend.services.mqtt import MQTTProcessingService

logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(
        self,
        broker_host: str | None = None,
        broker_port: int | None = None,
        topics: list[str] | None = None,
        client_id: str | None = None,
    ) -> None:
        self.broker_host = broker_host or getattr(settings, "MQTT_BROKER_HOST", "mosquitto")
        self.broker_port = broker_port or getattr(settings, "MQTT_BROKER_PORT", 1883)
        self.topics = topics or getattr(settings, "MQTT_TOPICS", ["sensors/#"])

        self.client = mqtt.Client(
            client_id=client_id or "django_mqtt_client",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self) -> None:
        self.connect()
        logger.info("Starting MQTT client loop...")
        self.client.loop_forever()

    def connect(self) -> None:
        try:
            logger.info("Connecting to MQTT broker at %s:%d...", self.broker_host, self.broker_port)
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: %s", e)
            raise ConnectionError(f"Could not connect to MQTT broker: {e}") from e

    def stop(self) -> None:
        logger.info("Stopping MQTT client...")
        self.client.disconnect()
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("Failed to connect to MQTT broker: %s", reason_code)
        else:
            logger.info("Connected to MQTT broker")
            for topic in self.topics:
                client.subscribe(topic)
                logger.info("Subscribed to topic: %s", topic)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        logger.warning("Disconnected from MQTT broker: %s", reason_code)

    def _on_message(self, client, userdata, message):
        try:
            topic = message.topic
            payload = message.payload.decode("utf-8")
            data = json.loads(payload)
            
            logger.debug(f"MQTT RX: {topic}")

            topic_parts = topic.split("/")
            if len(topic_parts) >= 3:
                station_code = topic_parts[1]
                msg_type = topic_parts[2]

                if msg_type == "status":
                    MQTTProcessingService.process_device_status(data)
                
                elif msg_type == "heartbeat":
                    MQTTProcessingService.process_station_heartbeat(station_code, data)
                
                else:
                    data['station_code'] = station_code 
                    MQTTProcessingService.process_measurement(data)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON on topic {message.topic}")
        except Exception as e:
            logger.exception(f"Error handling MQTT message: {e}")