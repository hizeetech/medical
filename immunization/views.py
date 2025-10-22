from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .models import ImmunizationSchedule, ImmunizationMaster, ImmunizationApproval, ImmunizationCertificate
from patients.models import MotherProfile, BabyProfile
from .forms import AddBabyImmunizationForm, AdministerImmunizationForm, ObservationForm, RescheduleForm
from accounts.decorators import role_required


@login_required
def schedule_view(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
    )
    babies = BabyProfile.objects.filter(mother=profile).order_by('date_of_birth')

    # Filters
    status_filter = request.GET.get('status', 'ALL').upper()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    start_date = None
    end_date = None
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid date filter. Please use YYYY-MM-DD.')

    qs = ImmunizationSchedule.objects.filter(baby__in=babies).select_related('baby')
    if status_filter in {'DUE', 'DONE', 'MISSED'}:
        qs = qs.filter(status=status_filter)
    if start_date:
        qs = qs.filter(scheduled_date__gte=start_date)
    if end_date:
        qs = qs.filter(scheduled_date__lte=end_date)

    schedules = qs.order_by('scheduled_date')

    # Group schedules by baby for easier rendering
    grouped_by_baby = []
    babies_by_id = {b.id: b for b in babies}
    items_by_baby = {}
    for s in schedules:
        items_by_baby.setdefault(s.baby_id, []).append(s)
    for b_id, items in items_by_baby.items():
        grouped_by_baby.append({'baby': babies_by_id.get(b_id), 'items': items})

    # Status summary counts (for current filtered set)
    status_counts = {
        'DUE': sum(1 for s in schedules if s.status == 'DUE'),
        'DONE': sum(1 for s in schedules if s.status == 'DONE'),
        'MISSED': sum(1 for s in schedules if s.status == 'MISSED'),
    }

    # Upcoming timeline: due items, soonest first
    upcoming = sorted((s for s in schedules if s.status == 'DUE'), key=lambda x: x.scheduled_date)

    return render(request, 'immunization/schedule.html', {
        'profile': profile,
        'babies': babies,
        'schedules': schedules,
        'grouped_by_baby': grouped_by_baby,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'start_date_filter': start_date_str or '',
        'end_date_filter': end_date_str or '',
        'upcoming': upcoming,
    })


@login_required
def update_schedule_status(request, pk):
    if request.method != 'POST':
        return redirect('immunization_schedule')

    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
    )

    try:
        schedule = ImmunizationSchedule.objects.select_related('baby').get(pk=pk)
    except ImmunizationSchedule.DoesNotExist:
        messages.error(request, 'Schedule not found.')
        return redirect('immunization_schedule')

    # Ownership check
    if schedule.baby.mother_id != profile.id:
        messages.error(request, 'You are not allowed to modify this schedule.')
        return redirect('immunization_schedule')

    action = (request.POST.get('action') or '').upper()
    if action not in {'DONE', 'MISSED', 'DUE'}:
        messages.error(request, 'Invalid action.')
        return redirect('immunization_schedule')

    schedule.status = action
    if action == 'DONE':
        schedule.date_completed = timezone.now().date()
        update_fields = ['status', 'date_completed']
    elif action == 'DUE':
        schedule.date_completed = None
        update_fields = ['status', 'date_completed']
    else:
        update_fields = ['status']
    schedule.save(update_fields=update_fields)
    messages.success(request, f'Status updated to {action.title()}.')
    return redirect('immunization_schedule')


# New: staff (doctor/nurse) can view all schedules
@login_required
def schedule_all_view(request):
    if not request.user.is_staff:
        messages.error(request, 'Staff access only.')
        return redirect('immunization_schedule')

    status_filter = request.GET.get('status', 'ALL').upper()
    qs = ImmunizationSchedule.objects.select_related('baby', 'baby__mother').all()
    if status_filter in {'DUE', 'DONE', 'MISSED'}:
        qs = qs.filter(status=status_filter)
    schedules = qs.order_by('scheduled_date')

    # Group by baby
    grouped_by_baby = []
    babies = BabyProfile.objects.all()
    babies_by_id = {b.id: b for b in babies}
    items_by_baby = {}
    for s in schedules:
        items_by_baby.setdefault(s.baby_id, []).append(s)
    for b_id, items in items_by_baby.items():
        grouped_by_baby.append({'baby': babies_by_id.get(b_id), 'items': items})

    status_counts = {
        'DUE': sum(1 for s in schedules if s.status == 'DUE'),
        'DONE': sum(1 for s in schedules if s.status == 'DONE'),
        'MISSED': sum(1 for s in schedules if s.status == 'MISSED'),
    }

    return render(request, 'immunization/schedule.html', {
        'profile': None,
        'babies': babies,
        'schedules': schedules,
        'grouped_by_baby': grouped_by_baby,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'start_date_filter': '',
        'end_date_filter': '',
        'upcoming': sorted((s for s in schedules if s.status == 'DUE'), key=lambda x: x.scheduled_date),
    })


@login_required
def manage_baby_immunizations(request, baby_id):
    if not request.user.is_staff:
        messages.error(request, 'Staff access only.')
        return redirect('immunization_schedule_all')
    try:
        baby = BabyProfile.objects.select_related('mother').get(pk=baby_id)
    except BabyProfile.DoesNotExist:
        messages.error(request, 'Baby not found.')
        return redirect('immunization_schedule_all')

    # Handle removal
    if request.method == 'POST' and 'remove_id' in request.POST:
        try:
            sid = int(request.POST.get('remove_id'))
            sched = ImmunizationSchedule.objects.get(pk=sid, baby=baby)
            sched.delete()
            messages.success(request, 'Immunization entry removed.')
        except Exception:
            messages.error(request, 'Unable to remove entry.')
        return redirect('immunization_manage_baby', baby_id=baby.id)

    # Add form
    form = AddBabyImmunizationForm(request.POST or None)
    if request.method == 'POST' and 'add' in request.POST:
        if form.is_valid():
            imm = form.cleaned_data['master']
            sd = form.cleaned_data.get('scheduled_date')
            notes = form.cleaned_data.get('notes') or ''
            if not sd:
                dob = baby.date_of_birth
                if imm.interval_unit == 'days':
                    sd = dob + timedelta(days=imm.interval_value)
                elif imm.interval_unit == 'weeks':
                    sd = dob + timedelta(weeks=imm.interval_value)
                elif imm.interval_unit == 'months':
                    sd = dob + timedelta(days=imm.interval_value * 30)
                else:
                    sd = dob
            ImmunizationSchedule.objects.create(
                baby=baby,
                vaccine_name=imm.name,
                scheduled_date=sd,
                notes=notes,
            )
            messages.success(request, 'Immunization added for baby.')
            return redirect('immunization_manage_baby', baby_id=baby.id)
        else:
            messages.error(request, 'Please correct the errors in the form.')

    # Filtering & sorting
    status_filter = (request.GET.get('status') or 'ALL').upper()
    sort_field = (request.GET.get('sort') or 'date').lower()  # date|name|status
    sort_dir = (request.GET.get('dir') or 'asc').lower()      # asc|desc

    qs = ImmunizationSchedule.objects.filter(baby=baby)
    if status_filter in {'DUE', 'DONE', 'MISSED'}:
        qs = qs.filter(status=status_filter)

    field_map = {
        'date': 'scheduled_date',
        'name': 'vaccine_name',
        'status': 'status',
    }
    order_field = field_map.get(sort_field, 'scheduled_date')
    if sort_dir == 'desc':
        order_field = f'-{order_field}'
    schedules = qs.order_by(order_field)

    return render(request, 'immunization/manage_baby.html', {
        'baby': baby,
        'form': form,
        'schedules': schedules,
        'status_filter': status_filter,
        'sort_field': sort_field,
        'sort_dir': sort_dir,
    })


@login_required
def baby_immunization_pdf(request, baby_id):
    # Allow staff, or the baby's mother (account owner)
    try:
        baby = BabyProfile.objects.select_related('mother', 'mother__user').get(pk=baby_id)
    except BabyProfile.DoesNotExist:
        messages.error(request, 'Baby not found.')
        return redirect('immunization_schedule')

    is_staff = request.user.is_staff
    is_mother_owner = hasattr(baby.mother, 'user') and baby.mother.user_id == request.user.id
    if not (is_staff or is_mother_owner):
        messages.error(request, 'You are not allowed to access this record.')
        # Route back to the appropriate schedule
        return redirect('immunization_schedule' if not is_staff else 'immunization_schedule_all')

    items = ImmunizationSchedule.objects.filter(baby=baby).order_by('scheduled_date')

    # Generate PDF (existing implementation below)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont('Helvetica-Bold', 16)
    c.drawString(40, height - 50, f"Immunization Record — {baby.name}")
    c.setFont('Helvetica', 11)
    c.drawString(40, height - 70, f"Mother: {baby.mother.full_name}")
    c.drawString(40, height - 85, f"DOB: {baby.date_of_birth:%Y-%m-%d}")

    y = height - 120
    c.setFont('Helvetica-Bold', 11)
    c.drawString(40, y, 'Vaccine')
    c.drawString(220, y, 'Recommended')
    c.drawString(340, y, 'Status')
    c.drawString(420, y, 'Given')
    c.line(40, y - 4, width - 40, y - 4)

    c.setFont('Helvetica', 10)
    y -= 20
    for s in items:
        if y < 60:
            c.showPage()
            c.setFont('Helvetica-Bold', 11)
            c.drawString(40, height - 50, 'Immunization Record (cont.)')
            y = height - 80
            c.setFont('Helvetica', 10)
        c.drawString(40, y, s.vaccine_name)
        c.drawString(220, y, f"{s.scheduled_date:%Y-%m-%d}")
        c.drawString(340, y, s.get_status_display())
        c.drawString(420, y, s.date_completed.strftime('%Y-%m-%d') if s.date_completed else '-')
        y -= 18

    c.showPage()
    c.save()
    buffer.seek(0)

    resp = HttpResponse(buffer.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="immunization-{baby.name}.pdf"'
    return resp


@login_required
def immunization_approve(request, baby_id):
    if not request.user.is_staff:
        messages.error(request, 'Staff access only.')
        return redirect('immunization_schedule_all')
    try:
        baby = BabyProfile.objects.get(pk=baby_id)
    except BabyProfile.DoesNotExist:
        messages.error(request, 'Baby not found.')
        return redirect('immunization_schedule_all')
    # Create or update approval
    approv, created = ImmunizationApproval.objects.get_or_create(
        baby=baby,
        defaults={'approved_by': request.user}
    )
    if not created and approv.approved_by_id != request.user.id:
        approv.approved_by = request.user
        approv.save(update_fields=['approved_by'])
    messages.success(request, f'Immunization schedules for {baby.name} approved and visible to mother.')
    return redirect('immunization_manage_baby', baby_id=baby.id)


@role_required('DOCTOR', 'NURSE', 'ADMIN')
def immunization_complete(request, pk):
    try:
        schedule = ImmunizationSchedule.objects.select_related('baby').get(pk=pk)
    except ImmunizationSchedule.DoesNotExist:
        messages.error(request, 'Schedule not found.')
        return redirect('immunization_schedule_all')
    form = AdministerImmunizationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            schedule.batch_number = form.cleaned_data.get('batch_number') or ''
            schedule.manufacturer = form.cleaned_data.get('manufacturer') or ''
            schedule.administration_site = form.cleaned_data.get('administration_site') or ''
            schedule.post_observation_notes = form.cleaned_data.get('notes') or ''
            administered_at = form.cleaned_data.get('administered_at')
            schedule.administered_at = administered_at or timezone.now()
            schedule.administered_by = request.user
            schedule.status = 'DONE'
            schedule.date_completed = (administered_at or timezone.now()).date()
            schedule.save(update_fields=['batch_number','manufacturer','administration_site','post_observation_notes','administered_at','administered_by','status','date_completed'])
            messages.success(request, 'Immunization marked as completed.')
            # Role-aware redirect
            if getattr(request.user, 'role', '') == 'NURSE':
                return redirect('nurse_dashboard')
            if getattr(request.user, 'role', '') == 'DOCTOR':
                return redirect('doctor_dashboard')
            return redirect('immunization_manage_baby', baby_id=schedule.baby_id)
        else:
            messages.error(request, 'Please correct the form errors.')
    return render(request, 'immunization/complete_form.html', {
        'schedule': schedule,
        'form': form,
        'title': 'Mark Immunization Completed'
    })


@role_required('DOCTOR', 'NURSE', 'ADMIN')
def immunization_observe(request, pk):
    try:
        schedule = ImmunizationSchedule.objects.select_related('baby').get(pk=pk)
    except ImmunizationSchedule.DoesNotExist:
        messages.error(request, 'Schedule not found.')
        return redirect('immunization_schedule_all')
    form = ObservationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            notes = form.cleaned_data['notes']
            schedule.post_observation_notes = notes
            schedule.save(update_fields=['post_observation_notes'])
            messages.success(request, 'Observation saved.')
            # Role-aware redirect
            if getattr(request.user, 'role', '') == 'NURSE':
                return redirect('nurse_dashboard')
            if getattr(request.user, 'role', '') == 'DOCTOR':
                return redirect('doctor_dashboard')
            return redirect('immunization_manage_baby', baby_id=schedule.baby_id)
        else:
            messages.error(request, 'Please add observation notes.')
    return render(request, 'immunization/observe_form.html', {'schedule': schedule, 'form': form, 'title': 'Post-vaccination Observation'})


@login_required
def immunization_reschedule(request, pk):
    if not request.user.is_staff:
        messages.error(request, 'Staff access only.')
        return redirect('immunization_schedule_all')
    try:
        schedule = ImmunizationSchedule.objects.select_related('baby').get(pk=pk)
    except ImmunizationSchedule.DoesNotExist:
        messages.error(request, 'Schedule not found.')
        return redirect('immunization_schedule_all')
    form = RescheduleForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            schedule.rescheduled_for = form.cleaned_data['rescheduled_for']
            schedule.reschedule_reason = form.cleaned_data.get('reason') or ''
            schedule.status = 'DUE'
            schedule.save(update_fields=['rescheduled_for','reschedule_reason','status'])
            messages.success(request, 'Immunization rescheduled.')
            return redirect('immunization_manage_baby', baby_id=schedule.baby_id)
        else:
            messages.error(request, 'Please provide a new date.')
    return render(request, 'immunization/reschedule_form.html', {'schedule': schedule, 'form': form, 'title': 'Reschedule Immunization'})


@login_required
def immunization_certificate(request, baby_id):
    # Allow staff, or the baby's mother (account owner)
    try:
        baby = BabyProfile.objects.select_related('mother', 'mother__user').get(pk=baby_id)
    except BabyProfile.DoesNotExist:
        messages.error(request, 'Baby not found.')
        return redirect('immunization_schedule')
    is_staff = request.user.is_staff
    is_mother_owner = hasattr(baby.mother, 'user') and baby.mother.user_id == request.user.id
    if not (is_staff or is_mother_owner):
        messages.error(request, 'You are not allowed to access this record.')
        return redirect('immunization_schedule' if not is_staff else 'immunization_schedule_all')
    # Ensure certificate exists if completed
    items = ImmunizationSchedule.objects.filter(baby=baby).order_by('scheduled_date')
    if items.exists() and not items.exclude(status='DONE').exists():
        snapshot = list(items.values('vaccine_name','scheduled_date','status','date_completed'))
        cert, _ = ImmunizationCertificate.objects.get_or_create(
            baby=baby,
            defaults={'generated_by': request.user, 'data_snapshot': {'items': snapshot}}
        )
        if cert.pk:
            cert.generated_by = request.user
            cert.data_snapshot = {'items': snapshot}
            cert.save(update_fields=['generated_by','data_snapshot'])
    cert = getattr(baby, 'immunization_certificate', None)
    return render(request, 'immunization/certificate.html', {
        'baby': baby,
        'certificate': cert,
        'items': items,
    })
