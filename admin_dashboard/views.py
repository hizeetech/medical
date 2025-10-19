from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
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
    metrics = {
        'total_patients': MotherProfile.objects.count(),
        'total_births': BabyProfile.objects.count(),
        'active_immunizations': ImmunizationSchedule.objects.filter(status='DUE').count(),
        'missed_vaccinations': ImmunizationSchedule.objects.filter(status='MISSED').count(),
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


# Role-specific dashboards
@role_required('NURSE')
def nurse_dashboard(request):
    due = ImmunizationSchedule.objects.filter(status='DUE').order_by('scheduled_date')[:10]
    missed = ImmunizationSchedule.objects.filter(status='MISSED').order_by('scheduled_date')[:10]
    babies = BabyProfile.objects.order_by('-created_at')[:5]
    return render(request, 'admin_dashboard/nurse.html', {
        'due_schedules': due,
        'missed_schedules': missed,
        'recent_babies': babies,
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
