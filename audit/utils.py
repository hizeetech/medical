from typing import Optional
from django.apps import apps
from django.utils import timezone

from .models import ActivityLog
from .middleware import get_current_user


def log_completion(instance, description: Optional[str] = None):
    """Utility to log an explicit completion event from views/services when needed."""
    ct = apps.get_model('contenttypes', 'ContentType').objects.get_for_model(instance.__class__)
    user = get_current_user()
    staff_name = None
    staff_id = None
    hospital_id = None
    if user and hasattr(user, 'role') and user.role != 'PATIENT':
        staff_name = f"{user.first_name} {user.last_name}".strip() or user.email
        staff_id = getattr(user, 'staff_id', None)
        hospital_id = getattr(user, 'hospital_clinic_id', None)

    now = timezone.localtime()
    ActivityLog.objects.create(
        action_type='complete',
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