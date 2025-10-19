from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
import json
from .models import Appointment
from patients.models import MotherProfile
from accounts.models import User
from centers.models import DoctorSchedule
from notifications.models import NotificationLog


def _normalize_doctor_slug(raw: str) -> str:
    s = slugify(raw or '')
    # Accept optional 'dr-' prefix
    return s[3:] if s.startswith('dr-') else s


def _find_doctor_by_slug(doctor_slug: str):
    target = _normalize_doctor_slug(doctor_slug)
    if not target:
        return None
    # Prefer role DOCTOR, but also include users with specialty filled
    candidates = User.objects.filter(role='DOCTOR') | User.objects.exclude(specialty__isnull=True).exclude(specialty='')
    # Evaluate into list to avoid duplicate evaluation of OR queryset
    candidates = list(candidates.distinct())
    for u in candidates:
        full = f"{u.first_name} {u.last_name}".strip()
        full_slug = slugify(full) if full else ''
        email_slug = slugify((u.email.split('@')[0]) if u.email else '')
        if target and (target == full_slug or target == email_slug):
            return u
    return None


@login_required
def appointments_list(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
    )
    appointments = Appointment.objects.filter(patient=profile).order_by('scheduled_at')
    return render(request, 'appointments/list.html', {
        'profile': profile,
        'appointments': appointments,
    })


@login_required
def appointment_new(request):
    doctor_slug = request.GET.get('doctor', '')
    step = request.GET.get('step', '1')
    selected_doctor = _find_doctor_by_slug(doctor_slug)

    # Build availability for next 60 days across all doctors
    candidates_qs = User.objects.filter(role='DOCTOR') | User.objects.exclude(specialty__isnull=True).exclude(specialty='')
    doctors = list(candidates_qs.distinct())

    today = timezone.localdate()
    upcoming_dates = [today + timedelta(days=i) for i in range(60)]

    schedules_qs = (DoctorSchedule.objects
                    .filter(doctor__in=doctors)
                    .select_related('doctor', 'center')
                    .order_by('doctor_id', 'day_of_week', 'start_time'))

    # Group schedules by doctor
    schedule_by_doc = {}
    for s in schedules_qs:
        schedule_by_doc.setdefault(s.doctor_id, []).append(s)

    dates_by_doc = {}
    times_by_date_by_doc = {}
    union_dates = set()
    union_times_by_date = {}
    # Meta maps
    meta_by_doctor_date_time = {}
    any_meta_by_date_time = {}

    available_doc_ids = set()

    for doc in doctors:
        doc_schedules = schedule_by_doc.get(doc.id, [])
        if not doc_schedules:
            continue
        # Map day_of_week -> list of schedule objects
        by_day = {}
        for s in doc_schedules:
            by_day.setdefault(s.day_of_week, []).append(s)
        doc_dates = []
        doc_times = {}
        doc_meta = {}
        for d in upcoming_dates:
            day_name = d.strftime('%A')
            ranges = by_day.get(day_name, [])
            if not ranges:
                continue
            date_key = d.strftime('%Y-%m-%d')
            doc_dates.append(date_key)
            slots = []
            for sched in ranges:
                dt_start = datetime.combine(d, sched.start_time)
                dt_end = datetime.combine(d, sched.end_time)
                cur = dt_start
                while cur < dt_end:
                    tstr = cur.strftime('%H:%M')
                    slots.append(tstr)
                    # Record meta per slot
                    doc_meta.setdefault(date_key, {})[tstr] = {
                        'center_name': getattr(sched.center, 'name', str(sched.center)),
                        'location': sched.location or '',
                        'doctor_id': doc.id,
                    }
                    # Union meta chooses first available
                    any_meta_by_date_time.setdefault(date_key, {})
                    any_meta_by_date_time[date_key].setdefault(tstr, {
                        'center_name': getattr(sched.center, 'name', str(sched.center)),
                        'location': sched.location or '',
                        'doctor_id': doc.id,
                    })
                    cur += timedelta(minutes=30)
            slots = sorted(set(slots))
            doc_times[date_key] = slots
            union_dates.add(date_key)
            union_times_by_date.setdefault(date_key, set()).update(slots)
        if doc_dates:
            dates_by_doc[doc.id] = sorted(set(doc_dates))
        if doc_times:
            times_by_date_by_doc[doc.id] = doc_times
            meta_by_doctor_date_time[doc.id] = doc_meta
            available_doc_ids.add(doc.id)

    # Restrict doctors to those with upcoming schedules
    doctors = [d for d in doctors if d.id in available_doc_ids]

    union_dates_sorted = sorted(union_dates)
    union_times_by_date_sorted = {k: sorted(list(v)) for k, v in union_times_by_date.items()}

    # Prepare doctors list for UI
    doctors_list = []
    for u in doctors:
        name = f"{u.first_name} {u.last_name}".strip()
        doctors_list.append({
            'id': u.id,
            'name': name or (u.email or '').split('@')[0],
            'email': u.email,
            'slug': slugify(name) if name else slugify((u.email or '').split('@')[0]),
            'specialty': getattr(u, 'specialty', ''),
        })

    # If a doctor was preselected via slug, prep single-doctor maps
    available_dates = []
    times_by_date = {}
    doctor = selected_doctor
    if doctor:
        available_dates = dates_by_doc.get(doctor.id, [])
        times_by_date = times_by_date_by_doc.get(doctor.id, {})

    # Handle form submission
    if request.method == 'POST':
        appointment_type = request.POST.get('appointment_type', 'ANTENATAL')
        message = request.POST.get('message', '')
        preferred_date = request.POST.get('preferred_date', '')
        preferred_time = request.POST.get('preferred_time', '')
        selected_doctor_id = request.POST.get('selected_doctor')

        assigned_doctor = None
        if doctor:
            assigned_doctor = doctor
        else:
            if selected_doctor_id == 'ANY' or not selected_doctor_id:
                # try to find any doctor with this slot
                found_id = None
                for doc_id, times_map in times_by_date_by_doc.items():
                    if preferred_date in times_map and preferred_time in times_map.get(preferred_date, []):
                        found_id = doc_id
                        break
                if found_id:
                    assigned_doctor = next((d for d in doctors if d.id == found_id), None)
            else:
                try:
                    doc_id_int = int(selected_doctor_id)
                except (TypeError, ValueError):
                    doc_id_int = None
                if doc_id_int:
                    assigned_doctor = next((d for d in doctors if d.id == doc_id_int), None)

        if not assigned_doctor:
            messages.error(request, 'Please select a doctor or pick an available slot.')
        else:
            # Validate selected slot exists for assigned doctor
            times_map = times_by_date_by_doc.get(assigned_doctor.id, {})
            valid = preferred_date in times_map and preferred_time in times_map.get(preferred_date, [])
            if not valid:
                messages.error(request, 'Selected date/time is not available for the chosen doctor.')
            else:
                try:
                    dt = datetime.strptime(f"{preferred_date} {preferred_time}", '%Y-%m-%d %H:%M')
                    scheduled_at = timezone.make_aware(dt, timezone.get_current_timezone())
                except Exception:
                    messages.error(request, 'Invalid date/time format.')
                    scheduled_at = None

                if scheduled_at:
                    profile, _ = MotherProfile.objects.get_or_create(
                        user=request.user,
                        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
                    )
                    appt = Appointment.objects.create(
                        patient=profile,
                        doctor=assigned_doctor,
                        appointment_type=appointment_type,
                        scheduled_at=scheduled_at,
                        notes=message,
                        status='SCHEDULED',
                    )
                    NotificationLog.objects.create(
                        recipient=assigned_doctor,
                        channel='IN_APP',
                        type='APPOINTMENT',
                        message=f"New appointment request from {profile.full_name or request.user.email} on {preferred_date} at {preferred_time}.",
                        meta={'appointment_id': appt.id, 'patient_id': profile.id, 'scheduled_at': scheduled_at.isoformat()}
                    )
                    messages.success(request, 'Your appointment request has been submitted.')
                    return redirect('appointments_list')

    context = {
        'doctor_slug': doctor_slug,
        'step': step,
        'doctor': doctor,
        'available_dates_json': json.dumps(available_dates),
        'times_by_date_json': json.dumps(times_by_date),
        'doctors_list_json': json.dumps(doctors_list),
        'any_available_dates_json': json.dumps(union_dates_sorted),
        'any_times_by_date_json': json.dumps(union_times_by_date_sorted),
        'available_dates_by_doctor_json': json.dumps(dates_by_doc),
        'times_by_date_by_doctor_json': json.dumps(times_by_date_by_doc),
        'any_slot_meta_by_date_time_json': json.dumps(any_meta_by_date_time),
        'slot_meta_by_doctor_json': json.dumps(meta_by_doctor_date_time),
        'doctor_id': getattr(doctor, 'id', None),
    }
    return render(request, 'appointments/new.html', context)
