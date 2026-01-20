"""
Realtime module for MQTT-based sensor data ingestion.

This module provides components for real-time data processing:
- MQTTClient: MQTT subscriber for sensor data
- Celery tasks for anomaly detection

Note: MQTTClient is imported lazily to avoid import errors during Django startup
if paho-mqtt is not yet installed.
"""

__all__ = ["MQTTClient"]


def __getattr__(name: str):
    """Lazy import to avoid import errors during Django startup."""
    if name == "MQTTClient":
        from pollution_backend.realtime.mqtt_client import MQTTClient
        return MQTTClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
