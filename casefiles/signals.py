from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from patients.models import BabyProfile
from immunization.models import ImmunizationSchedule

from .models import (
    BabyCaseFile,
    BabyCaseActivityLog,
)


@receiver(post_save, sender=BabyProfile)
def create_baby_casefile(sender, instance: BabyProfile, created: bool, **kwargs):
    if not created:
        return
    # Ensure a hospital_id exists (also handled in model.save)
    if not instance.hospital_id:
        # Fallback safeguard if save() didn't set it
        instance.hospital_id = f"BHB-{instance.id or timezone.now().strftime('%y%m%d%H%M')}"
        instance.save(update_fields=['hospital_id'])
    # Create the baby case file
    case_file, _ = BabyCaseFile.objects.get_or_create(
        baby=instance,
        defaults={'created_by': instance.registered_by}
    )
    BabyCaseActivityLog.objects.create(
        case_file=case_file,
        user=instance.registered_by,
        action='Baby case file created',
        notes=f"Registered by: {getattr(instance.registered_by, 'email', '')}"
    )


@receiver(post_save, sender=ImmunizationSchedule)
def log_immunization_to_baby_casefile(sender, instance: ImmunizationSchedule, **kwargs):
    # Log key updates into baby case file activity timeline
    try:
        case_file = instance.baby.baby_case_file
    except BabyCaseFile.DoesNotExist:
        return

    status_action = {
        'DUE': 'Immunization scheduled',
        'DONE': 'Immunization completed',
        'MISSED': 'Immunization missed',
    }.get(instance.status, 'Immunization updated')

    who = instance.administered_by or instance.approved_by
    who_label = getattr(who, 'email', None) or getattr(who, 'full_name', '') or 'System'

    note_bits = []
    if instance.rescheduled_for:
        note_bits.append(f"Rescheduled for {instance.rescheduled_for:%Y-%m-%d}")
    if instance.batch_number:
        note_bits.append(f"Batch {instance.batch_number}")
    if instance.manufacturer:
        note_bits.append(instance.manufacturer)
    if instance.administration_site:
        note_bits.append(f"Site {instance.administration_site}")
    if instance.post_observation_notes:
        note_bits.append("Observation notes added")

    BabyCaseActivityLog.objects.create(
        case_file=case_file,
        user=who,
        action=f"{status_action}: {instance.vaccine_name}",
        notes=f"On {instance.scheduled_date:%Y-%m-%d}. " + ("; ".join(note_bits) if note_bits else "")
    )