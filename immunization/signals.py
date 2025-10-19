from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from patients.models import BabyProfile
from immunization.models import ImmunizationSchedule, ImmunizationMaster
from notifications.tasks import send_immunization_notifications


@receiver(post_save, sender=ImmunizationSchedule)
def immunization_post_save(sender, instance: ImmunizationSchedule, created: bool, **kwargs):
    # Notify on creation or meaningful updates
    if created or kwargs.get('update_fields'):
        try:
            send_immunization_notifications.delay(instance.pk)
        except Exception:
            # Fallback: call synchronously if broker unavailable
            try:
                send_immunization_notifications(instance.pk)
            except Exception:
                pass

# New: auto-create schedule entries when a baby is registered
@receiver(post_save, sender=BabyProfile)
def create_immunization_schedule(sender, instance: BabyProfile, created: bool, **kwargs):
    if not created:
        return
    immunizations = ImmunizationMaster.objects.filter(is_active=True)
    dob = instance.date_of_birth
    for imm in immunizations:
        # Calculate due date based on interval unit
        if imm.interval_unit == 'days':
            due_date = dob + timedelta(days=imm.interval_value)
        elif imm.interval_unit == 'weeks':
            due_date = dob + timedelta(weeks=imm.interval_value)
        elif imm.interval_unit == 'months':
            # Approximate months as 30 days; switch to relativedelta if needed later
            due_date = dob + timedelta(days=imm.interval_value * 30)
        else:
            due_date = dob
        ImmunizationSchedule.objects.create(
            baby=instance,
            vaccine_name=imm.name,
            scheduled_date=due_date,
            notes=imm.description or '',
        )