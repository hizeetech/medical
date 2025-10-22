from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from .models import MotherProfile, VitalSigns, PostnatalCareRecord, BabyProfile
from .forms import MotherProfileForm
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from datetime import datetime, date
from barcode import Code128
from barcode.writer import ImageWriter
from django.db.models import Q


@login_required
def dashboard(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': '',
            'phone_number': request.user.phone_number or '',
        }
    )

    show_biodata_modal = bool(request.session.pop('newly_signed_up', False))
    form = MotherProfileForm(instance=profile)
    # Dashboard data from backend
    try:
        from appointments.models import Appointment
        next_appointment = Appointment.objects.filter(patient=profile, status='SCHEDULED').order_by('scheduled_at').first()
    except Exception:
        next_appointment = None

    # Immunization: compute from baby schedules, not appointments
    try:
        from immunization.models import ImmunizationSchedule
        today = date.today()
        qs = ImmunizationSchedule.objects.select_related('baby').filter(baby__mother=profile)
        next_immunization = qs.filter(status='DUE', scheduled_date__gte=today).order_by('scheduled_date').first()
        due_immunizations = ImmunizationSchedule.objects.filter(baby__mother=profile, status='DUE', visible_to_mother=True).order_by('scheduled_date')
        upcoming_immunizations = ImmunizationSchedule.objects.filter(baby__mother=profile, status='DUE', visible_to_mother=True).order_by('scheduled_date')[:5]
        completed_immunizations = qs.filter(status='DONE').order_by('-date_completed', '-scheduled_date')[:5]
        # Missed = explicit MISSED or any past-due not completed
        missed_immunizations = qs.filter(Q(status='MISSED') | (Q(status='DUE') & Q(scheduled_date__lt=today))).order_by('-scheduled_date')[:5]
    except Exception:
        next_immunization = None
        upcoming_immunizations = []
        completed_immunizations = []
        missed_immunizations = []

    recent_vitals = VitalSigns.objects.filter(mother=profile).order_by('-recorded_at').first()
    latest_postnatal = PostnatalCareRecord.objects.filter(mother=profile).order_by('-created_at').first()

    # Billing data
    try:
        from billing.models import Invoice
        recent_invoices = Invoice.objects.filter(patient=profile).order_by('-created_at')[:5]
        outstanding_invoices = Invoice.objects.filter(patient=profile, status__in=['PENDING', 'FAILED']).order_by('-created_at')[:5]
    except Exception:
        recent_invoices = []
        outstanding_invoices = []

    # Babies linked to this mother
    babies = BabyProfile.objects.filter(mother=profile).order_by('date_of_birth')

    return render(request, 'patients/dashboard.html', {
        'profile': profile,
        'show_biodata_modal': show_biodata_modal,
        'biodata_form': form,
        'next_appointment': next_appointment,
        'recent_vitals': recent_vitals,
        'latest_postnatal': latest_postnatal,
        'next_immunization': next_immunization,
        'upcoming_immunizations': upcoming_immunizations,
        'completed_immunizations': completed_immunizations,
        'missed_immunizations': missed_immunizations,
        'recent_invoices': recent_invoices,
        'outstanding_invoices': outstanding_invoices,
        'babies': babies,
    })


@login_required
def record_vitals(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
    )
    vitals = VitalSigns.objects.filter(mother=profile).order_by('-recorded_at')
    return render(request, 'patients/record_vitals.html', {
        'profile': profile,
        'vitals': vitals,
    })


@login_required
def postnatal_plan(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
    )
    records = PostnatalCareRecord.objects.filter(mother=profile).order_by('-created_at')
    return render(request, 'patients/postnatal_plan.html', {
        'profile': profile,
        'records': records,
    })


@login_required
def baby_profile_view(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={'full_name': '', 'phone_number': request.user.phone_number or ''}
    )
    babies = BabyProfile.objects.filter(mother=profile).order_by('date_of_birth')
    return render(request, 'patients/baby_profile.html', {
        'profile': profile,
        'babies': babies,
    })


@login_required
def profile_complete(request):
    profile = MotherProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = MotherProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            saved = form.save()
            # Sync key fields back to User so Admin shows them under Personal info
            user = request.user
            fields_to_update = []
            if saved.phone_number and saved.phone_number != user.phone_number:
                user.phone_number = saved.phone_number
                fields_to_update.append('phone_number')
            if saved.full_name:
                parts = saved.full_name.strip().split(' ', 1)
                first = parts[0] if parts else ''
                last = parts[1] if len(parts) > 1 else ''
                if first != user.first_name:
                    user.first_name = first
                    fields_to_update.append('first_name')
                if last != user.last_name:
                    user.last_name = last
                    fields_to_update.append('last_name')
            if saved.profile_picture and not user.avatar:
                user.avatar = saved.profile_picture
                fields_to_update.append('avatar')
            if fields_to_update:
                user.save(update_fields=fields_to_update)
            messages.success(request, 'Bio-data saved successfully.')
        else:
            messages.error(request, 'Please correct the errors in the bio-data form.')
    return redirect('dashboard')


@login_required
def profile_edit(request):
    profile, _ = MotherProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': '',
            'phone_number': request.user.phone_number or '',
        }
    )

    if request.method == 'POST':
        form = MotherProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            saved = form.save()
            # Sync key fields back to User for visibility in Admin
            user = request.user
            fields_to_update = []
            if saved.phone_number and saved.phone_number != user.phone_number:
                user.phone_number = saved.phone_number
                fields_to_update.append('phone_number')
            if saved.full_name:
                parts = saved.full_name.strip().split(' ', 1)
                first = parts[0] if parts else ''
                last = parts[1] if len(parts) > 1 else ''
                if first != user.first_name:
                    user.first_name = first
                    fields_to_update.append('first_name')
                if last != user.last_name:
                    user.last_name = last
                    fields_to_update.append('last_name')
            if saved.profile_picture and not user.avatar:
                user.avatar = saved.profile_picture
                fields_to_update.append('avatar')
            if fields_to_update:
                user.save(update_fields=fields_to_update)
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = MotherProfileForm(instance=profile)

    return render(request, 'patients/profile_edit.html', {
        'profile': profile,
        'form': form,
    })


@login_required
def member_card_pdf(request):
    profile = MotherProfile.objects.get(user=request.user)

    # Prepare barcode image in memory
    barcode_buffer = BytesIO()
    code = Code128(profile.member_id, writer=ImageWriter())
    code.write(barcode_buffer, options={
        'module_width': 0.25,
        'module_height': 10.0,
        'quiet_zone': 2.0,
        'write_text': False,
    })
    barcode_buffer.seek(0)
    barcode_img = ImageReader(barcode_buffer)
    img_w, img_h = barcode_img.getSize()

    # Generate PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # Card dimensions
    card_w = 86 * mm
    card_h = 54 * mm
    x = (width - card_w) / 2
    y = height - card_h - 40 * mm
    padding = 4 * mm
    header_h = 14 * mm

    # Card background
    c.setFillColorRGB(1, 1, 1)
    c.roundRect(x, y, card_w, card_h, 6 * mm, stroke=1, fill=1)

    # Header bar
    c.setFillColorRGB(0.11, 0.53, 0.95)  # Bootstrap primary-ish
    c.roundRect(x, y + card_h - header_h, card_w, header_h, 6*mm, stroke=0, fill=1)
    c.setFillColorRGB(1,1,1)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(x + card_w/2, y + card_h - header_h/2 - 2*mm, "Medical Care - Member Card")

    # Profile photo
    details_top = y + card_h - header_h - padding
    photo_size = 24 * mm
    photo_x = x + padding
    photo_y = details_top - photo_size
    if profile.profile_picture:
        try:
            photo = ImageReader(profile.profile_picture.path)
            c.drawImage(photo, photo_x, photo_y, width=photo_size, height=photo_size, mask='auto')
        except Exception:
            pass
    else:
        # Placeholder
        c.setStrokeColorRGB(0.8,0.8,0.8)
        c.rect(photo_x, photo_y, photo_size, photo_size)

    # Member details
    text_x = photo_x + photo_size + 6*mm
    text_y = details_top
    line_gap = 5 * mm
    c.setFillColorRGB(0,0,0)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(text_x, text_y, profile.full_name or request.user.email)
    c.setFont("Helvetica", 10)
    c.drawString(text_x, text_y - line_gap, f"Member ID: {profile.member_id}")
    c.drawString(text_x, text_y - 2*line_gap, f"Email: {request.user.email}")
    # Only render phone if there's enough vertical space above the barcode
    # Estimate barcode area top and ensure phone baseline stays above it with margin
    # (barcode will be drawn on the right side under text)
    # Compute barcode geometry first
    img_w, img_h = barcode_img.getSize()
    right_width = x + card_w - padding - text_x
    max_barcode_h = 10 * mm
    barcode_h = min(max_barcode_h, right_width * (img_h / img_w))
    barcode_x = text_x
    barcode_y = y + padding
    barcode_top = barcode_y + barcode_h
    phone_y = text_y - 3*line_gap
    if profile.phone_number and phone_y > barcode_top + (2 * mm):
        c.drawString(text_x, phone_y, f"Phone: {profile.phone_number}")

    # Barcode at bottom
    # Draw barcode under the text block on the right side to avoid overlapping the photo
    c.drawImage(barcode_img, barcode_x, barcode_y, width=right_width, height=barcode_h)
    # Optional divider line above barcode for visual separation
    c.setStrokeColorRGB(0.85, 0.85, 0.85)
    c.line(barcode_x, barcode_top + 2*mm, barcode_x + right_width, barcode_top + 2*mm)

    # Issue date (place under the barcode)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.4,0.4,0.4)
    # Position the issued date centered directly below the barcode, while
    # keeping it within the card bottom padding area
    issued_y = barcode_y - 2 * mm
    if issued_y < y + 1.5 * mm:
        issued_y = y + 1.5 * mm
    c.drawCentredString(barcode_x + right_width / 2, issued_y, f"Issued: {datetime.utcnow():%Y-%m-%d}")

    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="member-card-{profile.member_id}.pdf"'
    return response
