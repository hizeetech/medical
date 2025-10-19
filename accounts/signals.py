from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from patients.models import MotherProfile


@receiver(user_signed_up)
def create_profile_and_flag_signup(request, user, **kwargs):
    # Create MotherProfile if not exists
    MotherProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': '',
            'phone_number': user.phone_number or '',
        }
    )
    # Flag session to show biodata modal after redirect to dashboard
    if request is not None and hasattr(request, 'session'):
        request.session['newly_signed_up'] = True