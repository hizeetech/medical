from datetime import date, timedelta
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from appointments.models import Appointment
from immunization.models import ImmunizationSchedule
from notifications.utils import send_email, send_sms
from notifications.models import NotificationLog

User = get_user_model()


@shared_task
def send_appointment_notifications(appointment_id: int):
    try:
        appt = Appointment.objects.select_related('patient', 'doctor').get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return False
    patient = appt.patient
    user = patient.user
    email = getattr(user, 'email', '')
    phone = patient.phone_number or getattr(user, 'phone_number', '')

    subject = f"Appointment {appt.get_appointment_type_display()} scheduled"
    html = f"""
    <p>Hello {patient.full_name},</p>
    <p>Your appointment ({appt.get_appointment_type_display()}) is scheduled at {appt.scheduled_at:%Y-%m-%d %H:%M}.</p>
    {f'<p>Assigned doctor: {appt.doctor.email}</p>' if appt.doctor else ''}
    <p>Thank you.</p>
    """
    ok_email = send_email(email, subject, html)
    try:
        NotificationLog.objects.create(recipient=user, channel='EMAIL', type='APPOINTMENT', message=subject, success=ok_email, meta={'backend': settings.EMAIL_BACKEND})
    except Exception:
        pass
    sms_text = f"Appointment {appt.get_appointment_type_display()} at {appt.scheduled_at:%Y-%m-%d %H:%M}"
    ok_sms, meta_sms = send_sms(phone, sms_text)
    try:
        NotificationLog.objects.create(recipient=user, channel='SMS', type='APPOINTMENT', message=sms_text, success=ok_sms, meta=meta_sms)
    except Exception:
        pass
    return True


@shared_task
def send_immunization_notifications(schedule_id: int):
    try:
        sched = ImmunizationSchedule.objects.select_related('baby', 'baby__mother', 'baby__mother__user').get(pk=schedule_id)
    except ImmunizationSchedule.DoesNotExist:
        return False
    mother = sched.baby.mother
    user = mother.user
    email = getattr(user, 'email', '')
    phone = mother.phone_number or getattr(user, 'phone_number', '')

    subject = f"Immunization scheduled: {sched.vaccine_name}"
    html = f"""
    <p>Hello {mother.full_name},</p>
    <p>{sched.vaccine_name} is scheduled for {sched.baby.name} on {sched.scheduled_date:%Y-%m-%d}.</p>
    <p>Status: {sched.get_status_display()}</p>
    """
    ok_email = send_email(email, subject, html)
    try:
        NotificationLog.objects.create(recipient=user, channel='EMAIL', type='REMINDER', message=subject, success=ok_email, meta={'backend': settings.EMAIL_BACKEND})
    except Exception:
        pass
    sms_text = f"{sched.baby.name}: {sched.vaccine_name} on {sched.scheduled_date:%Y-%m-%d}"
    ok_sms, meta_sms = send_sms(phone, sms_text)
    try:
        NotificationLog.objects.create(recipient=user, channel='SMS', type='REMINDER', message=sms_text, success=ok_sms, meta=meta_sms)
    except Exception:
        pass
    return True


@shared_task
def send_immunization_reminder(schedule_id: int):
    today = date.today()
    try:
        sched = ImmunizationSchedule.objects.select_related('baby', 'baby__mother', 'baby__mother__user').get(pk=schedule_id)
    except ImmunizationSchedule.DoesNotExist:
        return False

    if sched.status == 'DONE' or today > sched.scheduled_date:
        return False

    mother = sched.baby.mother
    user = mother.user
    email = getattr(user, 'email', '')
    phone = mother.phone_number or getattr(user, 'phone_number', '')

    subject = f"Reminder: {sched.vaccine_name} on {sched.scheduled_date:%Y-%m-%d}"
    html = f"""
    <p>Hello {mother.full_name},</p>
    <p>Reminder: {sched.vaccine_name} for {sched.baby.name} is scheduled on {sched.scheduled_date:%Y-%m-%d}.</p>
    """
    ok_email = send_email(email, subject, html)
    try:
        NotificationLog.objects.create(recipient=user, channel='EMAIL', type='REMINDER', message=subject, success=ok_email, meta={'backend': settings.EMAIL_BACKEND})
    except Exception:
        pass
    sms_text = f"Reminder: {sched.vaccine_name} on {sched.scheduled_date:%Y-%m-%d}"
    ok_sms, meta_sms = send_sms(phone, sms_text)
    try:
        NotificationLog.objects.create(recipient=user, channel='SMS', type='REMINDER', message=sms_text, success=ok_sms, meta=meta_sms)
    except Exception:
        pass
    return True


@shared_task
def send_appointment_reminder(appointment_id: int):
    now = timezone.now()
    try:
        appt = Appointment.objects.select_related('patient', 'patient__user').get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return False

    # stop reminders if completed/cancelled or past date
    if appt.status in {'COMPLETED', 'CANCELLED', 'MISSED'} or now.date() > appt.scheduled_at.date():
        return False

    patient = appt.patient
    user = patient.user
    email = getattr(user, 'email', '')
    phone = patient.phone_number or getattr(user, 'phone_number', '')

    subject = f"Reminder: {appt.get_appointment_type_display()} at {appt.scheduled_at:%Y-%m-%d %H:%M}"
    html = f"""
    <p>Hello {patient.full_name},</p>
    <p>Reminder: Your appointment ({appt.get_appointment_type_display()}) is at {appt.scheduled_at:%Y-%m-%d %H:%M}.</p>
    """
    ok_email = send_email(email, subject, html)
    try:
        NotificationLog.objects.create(recipient=user, channel='EMAIL', type='REMINDER', message=subject, success=ok_email, meta={'backend': settings.EMAIL_BACKEND})
    except Exception:
        pass
    sms_text = f"Reminder: {appt.get_appointment_type_display()} at {appt.scheduled_at:%Y-%m-%d %H:%M}"
    ok_sms, meta_sms = send_sms(phone, sms_text)
    try:
        NotificationLog.objects.create(recipient=user, channel='SMS', type='REMINDER', message=sms_text, success=ok_sms, meta=meta_sms)
    except Exception:
        pass
    return True


@shared_task
def send_daily_immunization_reminders():
    today = date.today()
    end = today + timedelta(days=3)
    qs = ImmunizationSchedule.objects.select_related('baby', 'baby__mother', 'baby__mother__user')\
        .filter(status='DUE', scheduled_date__range=(today, end))
    count = 0
    for sched in qs:
        send_immunization_reminder.delay(sched.pk)
        count += 1
    return count


@shared_task
def send_daily_appointment_reminders():
    now = timezone.now()
    qs = Appointment.objects.select_related('patient', 'patient__user')\
        .filter(status='SCHEDULED', scheduled_at__date__gte=now.date())
    count = 0
    for appt in qs:
        send_appointment_reminder.delay(appt.pk)
        count += 1
    return count