from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from allauth.account.signals import user_signed_up
from patients.models import MotherProfile
from .models import FacilityExcelUpload
from .utils import get_facility_data


@receiver(user_signed_up)
def create_profile_and_flag_signup(sender, request, user, **kwargs):
    # Create MotherProfile if not exists
    MotherProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': '',
            'phone_number': getattr(user, 'phone_number', '') or '',
        }
    )
    # Flag session to show biodata modal after redirect to dashboard
    if request is not None and hasattr(request, 'session'):
        request.session['newly_signed_up'] = True


def _clear_facility_cache(*args, **kwargs):
    try:
        get_facility_data.cache_clear()
    except Exception:
        # Cache may not be initialized yet; ignore
        pass


@receiver(post_save, sender=FacilityExcelUpload)
def facility_excel_uploaded(sender, instance, **kwargs):
    _clear_facility_cache()


@receiver(post_delete, sender=FacilityExcelUpload)
def facility_excel_deleted(sender, instance, **kwargs):
    _clear_facility_cache()