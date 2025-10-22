from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from patients.models import BabyProfile
from immunization.models import ImmunizationSchedule, ImmunizationMaster, ImmunizationApproval, VaccinationEventLog, ImmunizationCertificate
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
    # Log status changes and completion
    if not created and kwargs.get('update_fields'):
        if 'status' in kwargs['update_fields']:
            VaccinationEventLog.objects.create(
                schedule=instance,
                event_type='STATUS_CHANGED',
                performed_by=None,
                details={'status': instance.status}
            )
        if instance.status == 'DONE':
            # When completed, log and check certificate eligibility
            VaccinationEventLog.objects.create(
                schedule=instance,
                event_type='ADMINISTERED',
                performed_by=instance.administered_by,
                details={
                    'administered_at': instance.administered_at.isoformat() if instance.administered_at else None,
                    'batch_number': instance.batch_number,
                    'manufacturer': instance.manufacturer,
                    'site': instance.administration_site,
                }
            )
            # Generate certificate if all schedules for baby are DONE
            remaining = ImmunizationSchedule.objects.filter(baby=instance.baby).exclude(status='DONE').exists()
            if not remaining:
                # Create or update certificate
                snapshot = list(
                    ImmunizationSchedule.objects.filter(baby=instance.baby).values(
                        'vaccine_name', 'scheduled_date', 'status', 'date_completed'
                    )
                )
                cert, _ = ImmunizationCertificate.objects.get_or_create(
                    baby=instance.baby,
                    defaults={
                        'generated_by': instance.administered_by,
                        'data_snapshot': {'items': snapshot},
                    }
                )
                if cert.pk:
                    cert.generated_by = instance.administered_by
                    cert.data_snapshot = {'items': snapshot}
                    cert.save(update_fields=['generated_by', 'data_snapshot'])
                VaccinationEventLog.objects.create(
                    schedule=instance,
                    event_type='CERTIFICATE_GENERATED',
                    performed_by=instance.administered_by,
                    details={'certificate_id': cert.pk}
                )

# Auto-create schedule entries when a baby is registered
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
            notes=imm.description or ''
        )

# When approval is created, expose schedules to mother and log event
@receiver(post_save, sender=ImmunizationApproval)
def on_approval_created(sender, instance: ImmunizationApproval, created: bool, **kwargs):
    # Mark all schedules visible
    ImmunizationSchedule.objects.filter(baby=instance.baby, visible_to_mother=False).update(visible_to_mother=True, approved_by=instance.approved_by, approved_at=timezone.now())
    # Log approval event on the most imminent schedule (if any)
    next_sched = ImmunizationSchedule.objects.filter(baby=instance.baby).order_by('scheduled_date').first()
    if next_sched:
        VaccinationEventLog.objects.create(
            schedule=next_sched,
            event_type='APPROVED',
            performed_by=instance.approved_by,
            details={'approval_id': instance.pk}
        )