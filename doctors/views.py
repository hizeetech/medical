from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from datetime import date
from accounts.decorators import role_required
from appointments.models import Appointment
from patients.models import DangerSignReport, MedicalRecord
from immunization.models import ImmunizationSchedule

# Reuse immunization performance helper from admin_dashboard
from admin_dashboard.views import get_immunization_stats

@role_required('DOCTOR')
def dashboard(request):
    now = timezone.now()
    upcoming_appointments = Appointment.objects.filter(
        doctor=request.user, status='SCHEDULED', scheduled_at__gte=now
    ).order_by('scheduled_at')[:10]
    upcoming_immunizations = Appointment.objects.filter(
        doctor=request.user, status='SCHEDULED', scheduled_at__gte=now
    ).order_by('scheduled_at')[:10]
    # Upcoming immunizations exclude overdue
    upcoming_immunizations_all = ImmunizationSchedule.objects.filter(status='DUE', scheduled_date__gte=now.date()).order_by('scheduled_date')[:10]
    # Today’s immunizations (all statuses)
    today_items = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').filter(scheduled_date=now.date()).order_by('baby__name', 'vaccine_name')

    # Overdue immunizations with filters
    today = now.date()
    overdue_qs = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').filter(
        status='DUE', scheduled_date__lt=today
    )
    over_q = (request.GET.get('over_q') or '').strip()
    over_vaccine = (request.GET.get('over_vaccine') or '').strip()
    over_start = (request.GET.get('over_start') or '').strip()
    over_end = (request.GET.get('over_end') or '').strip()
    over_days = (request.GET.get('over_days') or '').strip()
    if over_q:
        overdue_qs = overdue_qs.filter(
            Q(baby__name__icontains=over_q) |
            Q(baby__mother__full_name__icontains=over_q) |
            Q(baby__mother__member_id__icontains=over_q) |
            Q(baby__mother__phone_number__icontains=over_q)
        )
    if over_vaccine:
        overdue_qs = overdue_qs.filter(vaccine_name__icontains=over_vaccine)
    try:
        if over_start:
            overdue_qs = overdue_qs.filter(scheduled_date__gte=date.fromisoformat(over_start))
    except Exception:
        pass
    try:
        if over_end:
            overdue_qs = overdue_qs.filter(scheduled_date__lte=date.fromisoformat(over_end))
    except Exception:
        pass
    try:
        if over_days:
            days_int = int(over_days)
            cutoff = today - timezone.timedelta(days=days_int)
            overdue_qs = overdue_qs.filter(scheduled_date__lte=cutoff)
    except Exception:
        pass
    overdue_schedules = overdue_qs.order_by('-scheduled_date')

    # Missed immunizations (explicit MISSED)
    missed_qs = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').filter(status='MISSED')
    miss_q = (request.GET.get('miss_q') or '').strip()
    miss_vaccine = (request.GET.get('miss_vaccine') or '').strip()
    miss_start = (request.GET.get('miss_start') or '').strip()
    miss_end = (request.GET.get('miss_end') or '').strip()
    miss_days = (request.GET.get('miss_days') or '').strip()
    if miss_q:
        missed_qs = missed_qs.filter(
            Q(baby__name__icontains=miss_q) |
            Q(baby__mother__full_name__icontains=miss_q) |
            Q(baby__mother__member_id__icontains=miss_q) |
            Q(baby__mother__phone_number__icontains=miss_q)
        )
    if miss_vaccine:
        missed_qs = missed_qs.filter(vaccine_name__icontains=miss_vaccine)
    try:
        if miss_start:
            missed_qs = missed_qs.filter(scheduled_date__gte=date.fromisoformat(miss_start))
    except Exception:
        pass
    try:
        if miss_end:
            missed_qs = missed_qs.filter(scheduled_date__lte=date.fromisoformat(miss_end))
    except Exception:
        pass
    try:
        if miss_days:
            days_int = int(miss_days)
            cutoff = today - timezone.timedelta(days=days_int)
            missed_qs = missed_qs.filter(scheduled_date__lte=cutoff)
    except Exception:
        pass
    missed_schedules = missed_qs.order_by('-scheduled_date')

    alert_queue = DangerSignReport.objects.filter(
        assigned_doctor=request.user, status='NEW'
    ).order_by('-created_at')[:10]

    recent_records = MedicalRecord.objects.filter(
        doctor=request.user
    ).order_by('-created_at')[:5]

    # Filters for immunization performance (consistent with nurse dashboard)
    range_key = (request.GET.get('range') or 'today').lower()
    vaccine = request.GET.get('vaccine') or None
    doc_immunization_perf = get_immunization_stats(range_key, vaccine)

    context = {
        'upcoming_appointments': upcoming_immunizations,
        'upcoming_immunizations_all': upcoming_immunizations_all,
        'overdue_schedules': overdue_schedules,
        'alert_queue': alert_queue,
        'recent_records': recent_records,
        'doc_immunization_perf': doc_immunization_perf,
        'today_immunizations': today_items,
        'missed_schedules': missed_schedules,
    }
    return render(request, 'doctors/dashboard.html', context)
