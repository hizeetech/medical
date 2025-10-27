from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete, pre_save
from allauth.account.signals import user_signed_up
from patients.models import MotherProfile
from .models import FacilityExcelUpload, User
from .utils import get_facility_data, parse_hospital_clinic_id, find_facility_name


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
    try:
        find_facility_name.cache_clear()
    except Exception:
        pass


@receiver(post_save, sender=FacilityExcelUpload)
def facility_excel_uploaded(sender, instance, **kwargs):
    _clear_facility_cache()


@receiver(post_delete, sender=FacilityExcelUpload)
def facility_excel_deleted(sender, instance, **kwargs):
    _clear_facility_cache()


@receiver(pre_save, sender=User)
def ensure_facility_fields(sender, instance: User, **kwargs):
    """Ensure facility_name and staff_id stay consistent with hospital_clinic_id before saving.
    This covers edits outside the admin forms and guards against blanks.
    """
    role = getattr(instance, 'role', 'PATIENT') or 'PATIENT'
    if role == 'PATIENT':
        # Clear staff-related fields for patients
        instance.hospital_clinic_id = None
        instance.staff_id = None
        instance.facility_name = None
        return

    hospital_id = getattr(instance, 'hospital_clinic_id', None) or None
    serial = getattr(instance, 'staff_serial_number', None)

    if hospital_id:
        parsed = parse_hospital_clinic_id(hospital_id)
        if parsed:
            state_code, lga_abbr, lga_number, facility_type, facility_number = parsed
            fac_name = find_facility_name(lga_number=lga_number, facility_type=facility_type, facility_number=facility_number, lga_abbr=lga_abbr)
            # Only set if missing or empty
            if not getattr(instance, 'facility_name', None):
                instance.facility_name = fac_name
            # Recompute staff_id defensively
            if serial is not None:
                try:
                    instance.staff_id = f"{hospital_id}/{int(serial):05d}"
                except Exception:
                    # leave staff_id unchanged if serial invalid
                    pass
        else:
            # malformed hospital id; ensure facility_name not stuck with stale value
            instance.facility_name = None
    else:
        # No hospital id; clear
        instance.facility_name = None
        instance.staff_id = None