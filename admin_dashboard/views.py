from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from datetime import date
import csv

from accounts.decorators import role_required
from patients.models import MotherProfile, BabyProfile
from appointments.models import Appointment
from immunization.models import ImmunizationSchedule
from django.db import models

try:
    from billing.models import Invoice
except Exception:
    Invoice = None


@role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST', 'PHARMACIST', 'LAB_TECH')
def index(request):
    now = timezone.now()
    today = now.date()
    metrics = {
        'total_patients': MotherProfile.objects.count(),
        'total_births': BabyProfile.objects.count(),
        'active_immunizations': ImmunizationSchedule.objects.filter(status='DUE').count(),
        # Count missed as any schedule in the past not marked DONE
        'missed_vaccinations': ImmunizationSchedule.objects.filter(scheduled_date__lt=today).exclude(status='DONE').count(),
        'upcoming_appointments': Appointment.objects.filter(status='SCHEDULED', scheduled_at__gte=now).order_by('scheduled_at')[:10],
    }

    if Invoice is not None:
        income = Invoice.objects.filter(status='PAID').aggregate(total_amount=models.Sum('amount'))
        outstanding = Invoice.objects.filter(status__in=['PENDING', 'FAILED']).aggregate(total_amount=models.Sum('amount'))
        metrics['income_total'] = income['total_amount'] or 0
        metrics['outstanding_total'] = outstanding['total_amount'] or 0

    return render(request, 'admin_dashboard/index.html', metrics)


@role_required('ADMIN', 'DOCTOR', 'NURSE')
def export_appointments_csv(request):
    now = timezone.now()
    qs = Appointment.objects.filter(scheduled_at__gte=now - timezone.timedelta(days=90)).order_by('-scheduled_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="appointments.csv"'
    writer = csv.writer(response)
    writer.writerow(['Patient', 'Doctor', 'Type', 'Scheduled At', 'Status'])
    for a in qs:
        writer.writerow([
            a.patient.full_name,
            getattr(a.doctor, 'email', ''),
            a.get_appointment_type_display(),
            timezone.localtime(a.scheduled_at).strftime('%Y-%m-%d %H:%M'),
            a.get_status_display(),
        ])
    return response


@role_required('ADMIN', 'NURSE')
def export_immunizations_csv(request):
    qs = ImmunizationSchedule.objects.select_related('baby__mother').order_by('scheduled_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="immunizations.csv"'
    writer = csv.writer(response)
    writer.writerow(['Mother', 'Baby', 'Vaccine', 'Scheduled Date', 'Status', 'Completed Date'])
    for s in qs:
        writer.writerow([
            s.baby.mother.full_name,
            s.baby.name,
            s.vaccine_name,
            s.scheduled_date.strftime('%Y-%m-%d'),
            s.get_status_display(),
            s.date_completed.strftime('%Y-%m-%d') if s.date_completed else '',
        ])
    return response

# --- Immunization performance helpers ---

def _get_range_dates(range_key: str, today):
    range_key = (range_key or 'today').lower()
    if range_key == 'week':
        start = today - timezone.timedelta(days=today.weekday())
        end = start + timezone.timedelta(days=6)
        label = 'this week'
    elif range_key == 'month':
        start = today.replace(day=1)
        end = today
        label = 'this month'
    else:
        start = today
        end = today
        label = 'today'
    return start, end, label


def get_immunization_stats(range_key: str = 'today', vaccine: str | None = None):
    today = timezone.now().date()
    start, end, label = _get_range_dates(range_key, today)

    base = ImmunizationSchedule.objects.all()
    if vaccine:
        base = base.filter(vaccine_name__iexact=vaccine)

    expected = base.filter(scheduled_date__range=(start, end)).count()
    completed = base.filter(status='DONE', date_completed__range=(start, end)).count()
    missed = base.filter(scheduled_date__lte=end).exclude(status='DONE').count()

    total = expected + completed + missed
    completion_rate = (completed / expected * 100.0) if expected else 0.0

    if label == 'today':
        title = "Today's Immunization Performance"
        summary = f"Out of {expected} scheduled immunizations today, {completed} were completed and {missed} were missed ({completion_rate:.0f}% completion rate)."
    elif label == 'this week':
        title = "Weekly Immunization Summary (Expected vs Completed vs Missed)"
        summary = f"Out of {expected} scheduled immunizations this week, {completed} were completed and {missed} were missed ({completion_rate:.0f}% completion rate)."
    else:
        title = "Monthly Immunization Summary (Expected vs Completed vs Missed)"
        summary = f"Out of {expected} scheduled immunizations this month, {completed} were completed and {missed} were missed ({completion_rate:.0f}% completion rate)."

    return {
        'range': range_key,
        'label': label,
        'start': start,
        'end': end,
        'expected': expected,
        'completed': completed,
        'missed': missed,
        'total': total,
        'completion_rate': completion_rate,
        'title': title,
        'summary_text': summary,
        'vaccine': vaccine or '',
    }


# Role-specific dashboards
@role_required('NURSE')
def nurse_dashboard(request):
    today = timezone.now().date()
    # Base querysets
    due = ImmunizationSchedule.objects.filter(status='DUE', scheduled_date__gte=today).order_by('scheduled_date')[:10]
    
    # Overdue base: DUE but past date
    overdue_qs = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').filter(
        status='DUE', scheduled_date__lt=today
    )
    # Filters for Overdue Immunizations
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
    overdue = overdue_qs.order_by('-scheduled_date')

    # Missed base: explicitly status MISSED
    missed_qs = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').filter(status='MISSED')
    # Filters for Missed Immunizations
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
    missed = missed_qs.order_by('-scheduled_date')

    babies = BabyProfile.objects.order_by('-created_at')[:5]
    # Chart filters
    range_key = (request.GET.get('range') or 'today').lower()
    vaccine = request.GET.get('vaccine') or None
    perf = get_immunization_stats(range_key, vaccine)
    # Today's immunizations (all statuses)
    today_items = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').filter(scheduled_date=today).order_by('baby__name', 'vaccine_name')
    return render(request, 'admin_dashboard/nurse.html', {
        'due_schedules': due,
        'overdue_schedules': overdue,
        'missed_schedules': missed,
        'recent_babies': babies,
        'immunization_perf': perf,
        'today_immunizations': today_items,
    })

@role_required('RECEPTIONIST')
def receptionist_dashboard(request):
    now = timezone.now()
    upcoming = Appointment.objects.filter(status='SCHEDULED', scheduled_at__gte=now).order_by('scheduled_at')[:10]
    recent = Appointment.objects.order_by('-scheduled_at')[:10]
    return render(request, 'admin_dashboard/receptionist.html', {
        'upcoming_appointments': upcoming,
        'recent_appointments': recent,
    })

@role_required('PHARMACIST')
def pharmacist_dashboard(request):
    invoices = []
    if Invoice is not None:
        invoices = Invoice.objects.select_related('patient').order_by('-created_at')[:15]
    # Optional: prescriptions via attachments
    from patients.models import MedicalRecordAttachment
    prescriptions = MedicalRecordAttachment.objects.filter(type='PRESCRIPTION').order_by('-uploaded_at')[:10]
    return render(request, 'admin_dashboard/pharmacist.html', {
        'invoices': invoices,
        'prescriptions': prescriptions,
    })

@role_required('LAB_TECH')
def lab_tech_dashboard(request):
    from patients.models import MedicalRecordAttachment
    tests = MedicalRecordAttachment.objects.filter(type='TEST').order_by('-uploaded_at')[:15]
    return render(request, 'admin_dashboard/lab_tech.html', {
        'tests': tests,
    })
