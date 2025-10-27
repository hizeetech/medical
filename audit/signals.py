from typing import Optional

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.apps import apps
from django.utils import timezone

from .models import ActivityLog
from .middleware import get_current_user


TARGET_APPS = (
    'immunization',
    'patients',
    'casefiles',
    'appointments',
)


def _is_completion(prev_val: Optional[str], new_val: Optional[str], prev_bool: Optional[bool], new_bool: Optional[bool]) -> bool:
    completed_states = {'COMPLETED', 'COMPLETE', 'DONE', 'FINISHED'}
    if prev_bool is False and new_bool is True:
        return True
    if (new_val or '').upper() in completed_states and (prev_val or '').upper() not in completed_states:
        return True
    return False


def _extract_domain_snapshot(instance):
    """Safely extract Mother/Baby/Vaccine context and dates from known models.

    Works for:
    - immunization.ImmunizationSchedule (direct fields)
    - immunization.VaccinationEventLog (via .schedule)
    - patients.BabyProfile (via mother)
    - patients.MotherProfile
    Returns a dict for ActivityLog.create(**snapshot).
    """
    snap = {}
    try:
        # VaccinationEventLog → schedule
        if instance.__class__.__name__ == 'VaccinationEventLog' and hasattr(instance, 'schedule') and instance.schedule:
            sched = instance.schedule
            instance = sched  # reuse handling below
        # ImmunizationSchedule
        if instance.__class__.__name__ == 'ImmunizationSchedule':
            baby = getattr(instance, 'baby', None)
            if baby:
                snap['baby_name'] = getattr(baby, 'name', None)
                snap['baby_hospital_id'] = getattr(baby, 'hospital_id', None)
                mother = getattr(baby, 'mother', None)
                if mother:
                    snap['mother_name'] = getattr(mother, 'full_name', None)
                    snap['mother_member_id'] = getattr(mother, 'member_id', None)
            snap['vaccine_name'] = getattr(instance, 'vaccine_name', None)
            snap['scheduled_date'] = getattr(instance, 'scheduled_date', None)
            snap['completed_date'] = getattr(instance, 'date_completed', None)
            return snap
        # BabyProfile
        if instance.__class__.__name__ == 'BabyProfile':
            snap['baby_name'] = getattr(instance, 'name', None)
            snap['baby_hospital_id'] = getattr(instance, 'hospital_id', None)
            mother = getattr(instance, 'mother', None)
            if mother:
                snap['mother_name'] = getattr(mother, 'full_name', None)
                snap['mother_member_id'] = getattr(mother, 'member_id', None)
            return snap
        # MotherProfile
        if instance.__class__.__name__ == 'MotherProfile':
            snap['mother_name'] = getattr(instance, 'full_name', None)
            snap['mother_member_id'] = getattr(instance, 'member_id', None)
            return snap
    except Exception:
        # Avoid breaking logging if relations are missing
        pass
    return snap


def _stamp_activity(action_type: str, instance, description: Optional[str] = None):
    ct = apps.get_model('contenttypes', 'ContentType').objects.get_for_model(instance.__class__)
    user = get_current_user()
    # Pull staff context from user if available
    staff_name = None
    staff_id = None
    hospital_id = None
    if user and hasattr(user, 'role') and user.role != 'PATIENT':
        staff_name = f"{user.first_name} {user.last_name}".strip() or user.email
        staff_id = getattr(user, 'staff_id', None)
        hospital_id = getattr(user, 'hospital_clinic_id', None)

    now = timezone.localtime()
    payload = dict(
        action_type=action_type,
        module=instance._meta.app_label,
        model=instance.__class__.__name__,
        action_description=description,
        content_type=ct,
        object_id=str(getattr(instance, 'pk', '')),
        user=user if getattr(user, 'is_authenticated', False) else None,
        staff_name=staff_name,
        staff_id=staff_id,
        hospital_clinic_id=hospital_id,
        action_datetime=now,
        action_date=now.date(),
        action_time=now.time(),
    )
    # Merge domain snapshot fields
    payload.update(_extract_domain_snapshot(instance))
    ActivityLog.objects.create(**payload)


def _connect_model(model):
    # pre_save to capture previous state for completion detection
    @receiver(pre_save, sender=model, dispatch_uid=f'audit_pre_save_{model._meta.label_lower}')
    def _audit_pre_save(sender, instance, **kwargs):
        prev_status = None
        prev_completed = None
        if getattr(instance, 'pk', None):
            try:
                prev = sender.objects.get(pk=instance.pk)
                prev_status = getattr(prev, 'status', None)
                prev_completed = getattr(prev, 'is_completed', None)
            except sender.DoesNotExist:
                pass
        setattr(instance, '_audit_prev_status', prev_status)
        setattr(instance, '_audit_prev_completed', prev_completed)

    @receiver(post_save, sender=model, dispatch_uid=f'audit_post_save_{model._meta.label_lower}')
    def _audit_post_save(sender, instance, created, **kwargs):
        if created:
            _stamp_activity('create', instance)
        else:
            # Detect completion transition if present
            prev_status = getattr(instance, '_audit_prev_status', None)
            prev_completed = getattr(instance, '_audit_prev_completed', None)
            new_status = getattr(instance, 'status', None)
            new_completed = getattr(instance, 'is_completed', None)
            if _is_completion(prev_status, new_status, prev_completed, new_completed):
                _stamp_activity('complete', instance)
            else:
                _stamp_activity('update', instance)

    @receiver(post_delete, sender=model, dispatch_uid=f'audit_post_delete_{model._meta.label_lower}')
    def _audit_post_delete(sender, instance, **kwargs):
        _stamp_activity('delete', instance)


# Connect to all models in configured target apps
for app_label in TARGET_APPS:
    try:
        for model in apps.get_app_config(app_label).get_models():
            _connect_model(model)
    except Exception:
        # app may not exist in the project or has no models
        continue