from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
import paho.mqtt.publish as publish

def broadcast_log(group_name, log_data):
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "system_log",
                    "data": {
                        "msg_type": "log",
                        **log_data
                    }
                }
            )
        except Exception as e:
            print(f"WS Broadcast error: {e}")

def broadcast_station_log(station_id, log):
    log_data = {
        "id": log.id,
        "station_id": station_id,
        "event_type": log.event_type,
        "message": log.message,
        "log_level": log.log_level,
        "timestamp": log.timestamp.isoformat()
    }
    broadcast_log(f"station_{station_id}_status", log_data)

def broadcast_sensor_log(sensor_id, log):
    log_data = {
        "id": log.id,
        "sensor_id": sensor_id,
        "event_type": log.event_type,
        "message": log.message,
        "log_level": log.log_level,
        "timestamp": log.timestamp.isoformat()
    }
    broadcast_log(f"sensor_{sensor_id}_status", log_data)

def broadcast_sensor_status(sensor_id, data):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"sensor_{sensor_id}_status",
            {
                "type": "status_update",
                "data": data,
            },
        )

def publish_mqtt_command(station_code, command_json):
    try:
        broker_host = getattr(settings, "MQTT_BROKER_HOST", "mosquitto")
        topic = f"sensors/{station_code}/command"
        publish.single(topic, command_json, hostname=broker_host)
    except Exception as e:
        print(f"MQTT Publish error: {e}")