from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SystemLog

@receiver(post_save, sender=SystemLog)
def broadcast_system_log(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.sensor_id:
        channel_layer = get_channel_layer()
        if channel_layer:
            group_name = f"sensor_{instance.sensor_id}_status"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "system_log",
                    "data": {
                        "msg_type": "log",
                        "id": instance.id,
                        "timestamp": instance.timestamp.isoformat() if instance.timestamp else None,
                        "event_type": instance.event_type,
                        "message": instance.message,
                        "log_level": instance.log_level,
                        "sensor_id": instance.sensor_id,
                    },
                },
            )
