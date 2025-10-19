from django.db.models.signals import post_save
from django.dispatch import receiver
from appointments.models import Appointment
from notifications.tasks import send_appointment_notifications


@receiver(post_save, sender=Appointment)
def appointment_post_save(sender, instance: Appointment, created: bool, **kwargs):
    # Notify on creation or when status changes / doctor assigned
    if created or kwargs.get('update_fields'):
        try:
            send_appointment_notifications.delay(instance.pk)
        except Exception:
            # Fallback: call synchronously if broker unavailable
            try:
                send_appointment_notifications(instance.pk)
            except Exception:
                pass