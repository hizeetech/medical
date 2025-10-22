from django.shortcuts import render, redirect, get_object_or_404
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
    # Support simple filtering for doctor view
    filter_q = (request.GET.get('filter') or 'ALL').upper()
    user = request.user
    if getattr(user, 'role', '') == 'DOCTOR' or user.is_staff:
        qs = Appointment.objects.filter(doctor=user)
        now = timezone.now()
        if filter_q == 'UPCOMING':
            qs = qs.filter(status='SCHEDULED', scheduled_at__gte=now)
        elif filter_q == 'COMPLETED':
            qs = qs.filter(status='COMPLETED')
        elif filter_q == 'CANCELLED':
            qs = qs.filter(status='CANCELLED')
        appointments = qs.order_by('scheduled_at')
        return render(request, 'appointments/list.html', {
            'appointments': appointments,
            'is_doctor_view': True,
            'current_filter': filter_q,
        })
    # Patient view shows their own appointments
    profile, _ = MotherProfile.objects.get_or_create(
        user=user,
        defaults={'full_name': '', 'phone_number': user.phone_number or ''}
    )
    appointments = Appointment.objects.filter(patient=profile).order_by('scheduled_at')
    return render(request, 'appointments/list.html', {
        'profile': profile,
        'appointments': appointments,
        'is_doctor_view': False,
        'current_filter': 'ALL',
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
    upcoming_dates = [today + timedelta(days=i) for i in range(60)
]

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
        # Build available dates and times for the next 60 days
        for date in upcoming_dates:
            dow = date.weekday()
            schedules_for_day = by_day.get(dow, [])
            if not schedules_for_day:
                continue
            date_key = date.strftime('%Y-%m-%d')
            slots = []
            for ds in schedules_for_day:
                # Add slots every 30 minutes within schedule window
                start_dt = timezone.make_aware(datetime.combine(date, ds.start_time))
                end_dt = timezone.make_aware(datetime.combine(date, ds.end_time))
                cur = start_dt
                while cur < end_dt:
                    slots.append(cur.strftime('%H:%M'))
                    # store meta for slot (center, doctor)
                    doc_meta.setdefault(date_key, {})[cur.strftime('%H:%M')] = {
                        'center': getattr(ds.center, 'name', ''),
                        'doctor_id': doc.id,
                    }
                    cur += timedelta(minutes=30)
            if slots:
                doc_dates.append(date_key)
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


@login_required
def appointment_detail(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    user = request.user
    is_doctor_or_staff = getattr(user, 'role', '') == 'DOCTOR' or user.is_staff
    can_update = is_doctor_or_staff and (appt.doctor_id == user.id or user.is_staff)

    # Patient can view only their own appointment
    if not is_doctor_or_staff:
        if not hasattr(appt.patient, 'user') or appt.patient.user_id != user.id:
            messages.error(request, 'You do not have permission to view this appointment.')
            return redirect('appointments_list')

    if request.method == 'POST':
        if not can_update:
            messages.error(request, 'You do not have permission to update this appointment.')
            return redirect('appointment_detail', pk=appt.pk)
        status = request.POST.get('status', appt.status)
        scheduled_date = request.POST.get('scheduled_date', '')
        scheduled_time = request.POST.get('scheduled_time', '')
        notes = request.POST.get('notes', appt.notes)

        # Update status
        if status in dict(Appointment.STATUS_CHOICES):
            appt.status = status
        else:
            messages.error(request, 'Invalid status value.')
            return redirect('appointment_detail', pk=appt.pk)

        # Optional reschedule
        if scheduled_date and scheduled_time:
            try:
                dt = datetime.strptime(f"{scheduled_date} {scheduled_time}", '%Y-%m-%d %H:%M')
                appt.scheduled_at = timezone.make_aware(dt, timezone.get_current_timezone())
            except Exception:
                messages.error(request, 'Invalid date/time format for rescheduling.')
                return redirect('appointment_detail', pk=appt.pk)

        appt.notes = notes
        appt.save()
        messages.success(request, 'Appointment updated successfully.')
        return redirect('appointment_detail', pk=appt.pk)

    return render(request, 'appointments/detail.html', {
        'appointment': appt,
        'is_doctor_view': is_doctor_or_staff,
        'can_update': can_update,
    })
