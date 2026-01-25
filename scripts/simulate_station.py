"""
IoT Station Simulator for Heartbeat.

Usage:
    python scripts/simulate_station.py --station WAW001 --interval 300
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("Connected to MQTT broker")
    else:
        logger.error("Failed to connect: %s", reason_code)


def main():
    parser = argparse.ArgumentParser(description="Simulate Station Heartbeat")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--station", default="WAW001", help="Station code")
    parser.add_argument("--interval", type=float, default=60.0, help="Interval in seconds (default: 60)")

    args = parser.parse_args()

    topic = f"sensors/{args.station}/heartbeat"
    client_id = f"station_{args.station}_sim"

    client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect

    logger.info("Connecting to %s:%d...", args.host, args.port)
    try:
        client.connect(args.host, args.port, keepalive=60)
        client.loop_start()
    except Exception as e:
        logger.error("Failed to connect: %s", e)
        return 1

    logger.info("Starting heartbeat to '%s' every %.1f seconds...", topic, args.interval)

    try:
        while True:
            payload = {
                "msg_type": "heartbeat",
                "station": args.station,
                "status": "alive",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            res = client.publish(topic, json.dumps(payload), qos=1)
            
            if res.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("Sent heartbeat: %s", payload)
            else:
                logger.error("Failed to send heartbeat: %s", res.rc)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Stopping...")
    
    client.loop_stop()
    client.disconnect()
    return 0

if __name__ == "__main__":
    exit(main())
