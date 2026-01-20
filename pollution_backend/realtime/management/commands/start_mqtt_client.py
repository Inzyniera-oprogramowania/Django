"""
Django management command to start the MQTT client.

This command runs an MQTT subscriber that listens to sensor topics
and processes incoming measurement data in real-time.

Usage:
    python manage.py start_mqtt_client

Docker usage:
    Add as a separate service in docker-compose.local.yml
"""

import logging
import signal
import sys
from types import FrameType

from django.core.management.base import BaseCommand

from pollution_backend.realtime.mqtt_client import MQTTClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Django management command to run the MQTT subscriber.

    This command starts an MQTT client that:
    - Connects to the configured MQTT broker
    - Subscribes to sensor data topics
    - Processes incoming measurements
    - Triggers anomaly detection

    The command runs indefinitely until terminated.
    """

    help = "Start the MQTT client to subscribe to sensor data topics"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mqtt_client: MQTTClient | None = None

    def add_arguments(self, parser) -> None:
        """Add optional command arguments."""
        parser.add_argument(
            "--host",
            type=str,
            help="MQTT broker hostname (default: from settings)",
        )
        parser.add_argument(
            "--port",
            type=int,
            help="MQTT broker port (default: from settings)",
        )

    def handle(self, *args, **options) -> None:
        """
        Execute the command.

        Initializes the MQTT client with optional host/port overrides,
        sets up signal handlers for graceful shutdown, and starts
        the client loop.

        Args:
            *args: Positional arguments
            **options: Command options including host and port
        """
        self.stdout.write(self.style.SUCCESS("Starting MQTT client..."))

        # Get optional overrides
        host = options.get("host")
        port = options.get("port")

        # Initialize MQTT client
        self.mqtt_client = MQTTClient(
            broker_host=host,
            broker_port=port,
        )

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            self.stdout.write("Connecting to MQTT broker...")
            self.mqtt_client.start()
        except ConnectionError as e:
            self.stderr.write(self.style.ERROR(f"Failed to connect: {e}"))
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nShutdown requested..."))
            self._shutdown()

    def _signal_handler(self, signum: int, frame: FrameType | None) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number received
            frame: Current stack frame
        """
        self.stdout.write(self.style.WARNING(f"\nReceived signal {signum}, shutting down..."))
        self._shutdown()

    def _shutdown(self) -> None:
        """Gracefully shut down the MQTT client."""
        if self.mqtt_client:
            self.mqtt_client.stop()
        self.stdout.write(self.style.SUCCESS("MQTT client stopped."))
        sys.exit(0)
