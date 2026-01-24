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

# TODO wszystko pobierane z bazy i cron, dodanie logów systemowych, zuzycia baterii, sygnał, uptime, reset?



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


# Track uptime across calls
_uptime_start = time.time()


def generate_device_status(sensor_id: int) -> dict:
    """
    Generate a device status payload with battery, signal, and uptime.

    Args:
        sensor_id: ID of the sensor

    Returns:
        Dictionary with device status data
    """
    # Simulate battery drain (starts at 100%, decreases slowly)
    elapsed_minutes = (time.time() - _uptime_start) / 60
    battery = max(5, 100 - int(elapsed_minutes * 0.5))  # Lose 0.5% per minute

    # Simulate signal strength fluctuation
    signal = random.randint(-80, -40)

    # Calculate uptime in seconds
    uptime = int(time.time() - _uptime_start)

    return {
        "sensor_id": sensor_id,
        "battery_percent": battery,
        "signal_rssi_dbm": signal,
        "uptime_seconds": uptime,
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


def on_message(client, userdata, msg):
    """Handle incoming messages."""
    global _uptime_start
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("command") == "RESET":
            logger.info("Received RESET command. Resetting uptime and battery.")
            _uptime_start = time.time()
    except Exception as e:
        logger.error("Failed to process message: %s", e)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulate an IoT sensor publishing MQTT messages",
    )
    # ... (skipping arguments, assuming they are unchanged until we modify main)
    # Actually, replacement content must match precisely.
    # I should target a smaller block inside main or define on_message before main.
    # Let's define on_message before main first.
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
    parser.add_argument(
        "--status",
        action="store_true",
        help="Send device status messages instead of measurements",
    )
    parser.add_argument(
        "--status-interval",
        type=float,
        default=30.0,
        help="Status publish interval in seconds (default: 30.0)",
    )

    args = parser.parse_args()

    # Build topic based on mode
    if args.status:
        topic = f"sensors/{args.station}/status"
    else:
        topic = f"sensors/{args.station}/{args.pollutant}"

    # Create MQTT client
    suffix = "_status" if args.status else "_meas"
    client = mqtt.Client(
        client_id=f"simulator_{args.sensor_id}{suffix}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message

    logger.info("Connecting to %s:%d...", args.host, args.port)
    try:
        client.connect(args.host, args.port, keepalive=60)
    except Exception as e:
        logger.error("Failed to connect: %s", e)
        return 1

    client.loop_start()

    # Subscribe to command topic
    command_topic = f"sensors/{args.station}/command"
    client.subscribe(command_topic)
    logger.info("Subscribed to command topic: %s", command_topic)

    # Determine interval and mode
    interval = args.status_interval if args.status else args.interval
    mode_name = "status" if args.status else "measurement"

    logger.info(
        "Publishing %s to topic '%s' every %.1f seconds (Ctrl+C to stop)",
        mode_name,
        topic,
        interval,
    )

    sent = 0
    try:
        while args.count == 0 or sent < args.count:
            if args.status:
                # Device status mode
                message = generate_device_status(sensor_id=args.sensor_id)
                payload = json.dumps(message)
                result = client.publish(topic, payload, qos=1)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(
                        "Published status: battery=%d%%, signal=%d dBm, uptime=%ds",
                        message["battery_percent"],
                        message["signal_rssi_dbm"],
                        message["uptime_seconds"],
                    )
                    sent += 1
                else:
                    logger.error("Failed to publish: %s", result.rc)
            else:
                # Measurement mode (original behavior)
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

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("\nStopping simulator...")

    client.loop_stop()
    client.disconnect()
    logger.info("Disconnected. Sent %d messages.", sent)
    return 0


if __name__ == "__main__":
    exit(main())
