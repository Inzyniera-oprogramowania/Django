import time
from django.core.management.base import BaseCommand
from pollution_backend.realtime.mqtt_client import MQTTClient

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            client = MQTTClient(client_id="django_mqtt_listener_cmd")
            client.start()
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            if 'client' in locals():
                client.stop()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to start MQTT Client: {e}'))
