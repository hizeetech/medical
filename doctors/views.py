from django.shortcuts import render
from django.utils import timezone
from accounts.decorators import role_required
from appointments.models import Appointment
from patients.models import DangerSignReport, MedicalRecord

@role_required('DOCTOR')
def dashboard(request):
    now = timezone.now()
    upcoming_appointments = Appointment.objects.filter(
        doctor=request.user, status='SCHEDULED', scheduled_at__gte=now
    ).order_by('scheduled_at')[:10]

    alert_queue = DangerSignReport.objects.filter(
        assigned_doctor=request.user, status='NEW'
    ).order_by('-created_at')[:10]

    recent_records = MedicalRecord.objects.filter(
        doctor=request.user
    ).order_by('-created_at')[:5]

    context = {
        'upcoming_appointments': upcoming_appointments,
        'alert_queue': alert_queue,
        'recent_records': recent_records,
    }
    return render(request, 'doctors/dashboard.html', context)
