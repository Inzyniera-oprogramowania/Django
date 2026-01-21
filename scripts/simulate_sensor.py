#!/usr/bin/env python3
"""
IoT Sensor Simulator for MQTT Testing.

This script simulates an IoT sensor publishing measurement data to the
Mosquitto MQTT broker. Use it to test the MQTT client integration.

Usage:
    python scripts/simulate_sensor.py

    # With custom parameters:
    python scripts/simulate_sensor.py --host localhost --port 1883 \\
        --station WAW001 --pollutant PM25 --sensor-id 1 --interval 5

Requirements:
    pip install paho-mqtt
"""

# TODO wszystko pobierane z bazy i cron

import argparse
import json
import logging
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default pollutant ranges (µg/m³)
POLLUTANT_RANGES = {
    "PM25": (5.0, 150.0),
    "PM10": (10.0, 200.0),
    "NO2": (5.0, 100.0),
    "O3": (10.0, 180.0),
    "SO2": (2.0, 50.0),
    "CO": (0.5, 10.0),
}


def generate_measurement(
    sensor_id: int,
    pollutant: str,
    unit: str = "µg/m³",
) -> dict:
    """
    Generate a random measurement payload.

    Args:
        sensor_id: ID of the sensor
        pollutant: Pollutant symbol (e.g., PM25, NO2)
        unit: Measurement unit

    Returns:
        Dictionary with measurement data
    """
    value_range = POLLUTANT_RANGES.get(pollutant, (0.0, 100.0))
    value = round(random.uniform(*value_range), 2)

    # Occasionally generate anomalous values (10% chance)
    if random.random() < 0.1:
        value = round(value * random.uniform(2.0, 3.0), 2)
        logger.warning("Generated anomalous value: %.2f", value)

    return {
        "sensor_id": sensor_id,
        "value": value,
        "unit": unit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to MQTT broker."""
    if reason_code == 0:
        logger.info("Connected to MQTT broker")
    else:
        logger.error("Failed to connect: %s", reason_code)


def on_publish(client, userdata, mid, reason_code, properties):
    """Callback when message is published."""
    logger.debug("Message published (mid=%d)", mid)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulate an IoT sensor publishing MQTT messages",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="MQTT broker host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    parser.add_argument(
        "--station",
        default="WAW001",
        help="Station code (default: WAW001)",
    )
    parser.add_argument(
        "--pollutant",
        default="PM25",
        choices=list(POLLUTANT_RANGES.keys()),
        help="Pollutant symbol (default: PM25)",
    )
    parser.add_argument(
        "--sensor-id",
        type=int,
        default=1,
        help="Sensor ID (default: 1)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Publish interval in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of messages to send (0 = infinite, default: 0)",
    )
    parser.add_argument(
        "--unit",
        default="µg/m³",
        help="Measurement unit (default: µg/m³)",
    )

    args = parser.parse_args()

    # Build topic
    topic = f"sensors/{args.station}/{args.pollutant}"

    # Create MQTT client
    client = mqtt.Client(
        client_id=f"simulator_{args.sensor_id}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.on_connect = on_connect
    client.on_publish = on_publish

    logger.info("Connecting to %s:%d...", args.host, args.port)
    try:
        client.connect(args.host, args.port, keepalive=60)
    except Exception as e:
        logger.error("Failed to connect: %s", e)
        return 1

    client.loop_start()

    logger.info(
        "Publishing to topic '%s' every %.1f seconds (Ctrl+C to stop)",
        topic,
        args.interval,
    )

    sent = 0
    try:
        while args.count == 0 or sent < args.count:
            measurement = generate_measurement(
                sensor_id=args.sensor_id,
                pollutant=args.pollutant,
                unit=args.unit,
            )
            payload = json.dumps(measurement)

            result = client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(
                    "Published: topic=%s, value=%.2f %s",
                    topic,
                    measurement["value"],
                    measurement["unit"],
                )
                sent += 1
            else:
                logger.error("Failed to publish: %s", result.rc)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("\nStopping simulator...")

    client.loop_stop()
    client.disconnect()
    logger.info("Disconnected. Sent %d messages.", sent)
    return 0


if __name__ == "__main__":
    exit(main())
