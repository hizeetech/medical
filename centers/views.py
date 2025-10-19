from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Center, DoctorSchedule


def centers_list(request):
    centers = Center.objects.all()
    return render(request, 'centers/index.html', {
        'centers': centers,
    })


def center_detail(request, slug):
    center = get_object_or_404(Center, slug=slug)

    # Load all schedules and group by doctor
    schedules = (DoctorSchedule.objects
                 .filter(center=center)
                 .select_related('doctor')
                 .order_by('doctor_id', 'day_of_week', 'start_time'))

    schedules_by_doctor = {}
    doctors_by_id = {}
    for sched in schedules:
        schedules_by_doctor.setdefault(sched.doctor_id, []).append(sched)
        # Cache doctor objects from select_related to avoid extra queries
        if sched.doctor_id not in doctors_by_id:
            doctors_by_id[sched.doctor_id] = sched.doctor

    # If no schedules, still show doctors assigned to the center
    if not schedules_by_doctor:
        # fallback to related doctors list
        for doc in center.related_doctors.all():
            doctors_by_id[doc.id] = doc
            schedules_by_doctor.setdefault(doc.id, [])

    # Build upcoming 7-day slots for each doctor based on day_of_week
    today = timezone.localdate()
    upcoming_dates = [today + timedelta(days=i) for i in range(7)]

    doctor_schedule_pairs = []
    for doc_id, doc in doctors_by_id.items():
        doc_schedules = schedules_by_doctor.get(doc_id, [])
        # Map day_of_week -> list of time ranges
        day_map = {}
        for s in doc_schedules:
            day_map.setdefault(s.day_of_week, []).append(f"{s.start_time:%H:%M} - {s.end_time:%H:%M}")

        slots = []
        for d in upcoming_dates:
            day_name = d.strftime('%A')
            times = day_map.get(day_name, [])
            slots.append({
                'date_label': d.strftime('%d %b (%a)'),
                'times': times,
            })

        doctor_schedule_pairs.append({
            'doctor': doc,
            'schedules': doc_schedules,
            'slots': slots,
        })

    return render(request, 'centers/detail.html', {
        'center': center,
        'doctor_schedule_pairs': doctor_schedule_pairs,
    })