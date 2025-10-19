from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpResponseBadRequest

from accounts.decorators import role_required
from accounts.models import User
from patients.models import MotherProfile, MedicalRecord, BabyProfile
from billing.models import Invoice
from immunization.models import ImmunizationSchedule
from .forms import MedicalRecordForm
from patients.models import MedicalRecord

from .models import (
    PatientCaseFile,
    VisitRecord,
    Prescription,
    LabResult,
    CaseBillingRecord,
    CaseAttachment,
    CaseActivityLog,
)
from .forms import VisitRecordForm, PrescriptionForm, LabResultForm, CaseAttachmentForm
from .forms import CaseBillingRecordForm, BabyProfileForm, CaseActivityLogForm


@login_required
def casefile_search(request):
    query = request.GET.get('q', '').strip()
    patients = []
    if query:
        patients = MotherProfile.objects.filter(
            Q(member_id__icontains=query) |
            Q(full_name__icontains=query)
        ).order_by('full_name')[:50]
    context = {
        'query': query,
        'patients': patients,
    }
    return render(request, 'casefiles/search.html', context)


@login_required
def casefile_detail(request, casefile_id=None):
    # When arriving from search, casefile_id is provided; otherwise create if missing
    if casefile_id:
        case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    else:
        return HttpResponseBadRequest('Missing case file.')

    context = {
        'case_file': case_file,
    }
    return render(request, 'casefiles/detail.html', context)


@login_required
def open_or_create_casefile(request, patient_id):
    patient = get_object_or_404(MotherProfile, id=patient_id)
    case_file, created = PatientCaseFile.objects.get_or_create(
        patient=patient,
        defaults={'created_by': request.user, 'primary_doctor': None}
    )
    if created:
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Case file created')
    return redirect('casefile_detail', casefile_id=case_file.id)


@login_required
def tab_patient_info(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    return render(request, 'casefiles/tabs/_patient_info.html', {
        'case_file': case_file,
        'patient': case_file.patient,
    })


@login_required
def tab_medical_history(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    # Show recent medical records for auto-population reference
    records = MedicalRecord.objects.filter(mother=case_file.patient).order_by('-created_at')[:10]
    form = MedicalRecordForm()
    return render(request, 'casefiles/tabs/_medical_history.html', {
        'case_file': case_file,
        'patient': case_file.patient,
        'records': records,
        'form': form,
    })


@login_required
def tab_visits(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    visits = case_file.visits.order_by('-date_of_visit')[:20]
    form = VisitRecordForm()
    return render(request, 'casefiles/tabs/_visits.html', {
        'case_file': case_file,
        'visits': visits,
        'form': form,
    })


@login_required
def tab_prescriptions(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    prescriptions = case_file.prescriptions.order_by('-created_at')[:50]
    form = PrescriptionForm()
    return render(request, 'casefiles/tabs/_prescriptions.html', {
        'case_file': case_file,
        'prescriptions': prescriptions,
        'form': form,
    })


@login_required
def tab_lab_results(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    lab_results = case_file.lab_results.order_by('-date_performed')[:50]
    form = LabResultForm()
    return render(request, 'casefiles/tabs/_lab_results.html', {
        'case_file': case_file,
        'lab_results': lab_results,
        'form': form,
    })


@login_required
def tab_billing(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    invoices = Invoice.objects.filter(patient=case_file.patient).order_by('-created_at')[:50]
    totals = invoices.aggregate(amount=Sum('amount'))
    billing_records = case_file.billing_records.order_by('-created_at')[:50]
    form = CaseBillingRecordForm()
    return render(request, 'casefiles/tabs/_billing.html', {
        'case_file': case_file,
        'invoices': invoices,
        'invoices_total': totals.get('amount') or 0,
        'billing_records': billing_records,
        'form': form,
    })


@login_required
def tab_maternity(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    babies = BabyProfile.objects.filter(mother=case_file.patient).order_by('date_of_birth')
    schedules = ImmunizationSchedule.objects.filter(baby__in=babies).order_by('scheduled_date')[:50]
    form = BabyProfileForm()
    return render(request, 'casefiles/tabs/_maternity.html', {
        'case_file': case_file,
        'babies': babies,
        'schedules': schedules,
        'form': form,
    })


@login_required
def tab_attachments(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    attachments = case_file.attachments.order_by('-created_at')[:50]
    form = CaseAttachmentForm()
    return render(request, 'casefiles/tabs/_attachments.html', {
        'case_file': case_file,
        'attachments': attachments,
        'form': form,
    })


@login_required
def tab_access(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    logs = case_file.activity_logs.order_by('-created_at')[:50]
    form = CaseActivityLogForm()
    return render(request, 'casefiles/tabs/_access.html', {
        'case_file': case_file,
        'logs': logs,
        'form': form,
    })


@login_required
@role_required('DOCTOR', 'NURSE')
def visit_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = VisitRecordForm(request.POST)
    if form.is_valid():
        visit = form.save(commit=False)
        visit.case_file = case_file
        visit.provider = request.user
        visit.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Visit added')
        return tab_visits(request, casefile_id)
    # Re-render with errors
    visits = case_file.visits.order_by('-date_of_visit')[:20]
    return render(request, 'casefiles/tabs/_visits.html', {'case_file': case_file, 'visits': visits, 'form': form})


@login_required
@role_required('DOCTOR')
def prescription_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = PrescriptionForm(request.POST)
    if form.is_valid():
        pres = form.save(commit=False)
        pres.case_file = case_file
        pres.prescribing_by = request.user
        pres.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Prescription added')
        return tab_prescriptions(request, casefile_id)
    prescriptions = case_file.prescriptions.order_by('-created_at')[:50]
    return render(request, 'casefiles/tabs/_prescriptions.html', {'case_file': case_file, 'prescriptions': prescriptions, 'form': form})


@login_required
@role_required('LAB_TECH')
def lab_result_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = LabResultForm(request.POST, request.FILES)
    if form.is_valid():
        lab = form.save(commit=False)
        lab.case_file = case_file
        lab.performed_by = request.user
        lab.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Lab result added')
        return tab_lab_results(request, casefile_id)
    lab_results = case_file.lab_results.order_by('-date_performed')[:50]
    return render(request, 'casefiles/tabs/_lab_results.html', {'case_file': case_file, 'lab_results': lab_results, 'form': form})


@login_required
@role_required('DOCTOR', 'NURSE', 'PHARMACIST', 'LAB_TECH')
def attachment_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = CaseAttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        att = form.save(commit=False)
        att.case_file = case_file
        att.uploaded_by = request.user
        att.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Attachment uploaded')
        return tab_attachments(request, casefile_id)
    attachments = case_file.attachments.order_by('-created_at')[:50]
    return render(request, 'casefiles/tabs/_attachments.html', {'case_file': case_file, 'attachments': attachments, 'form': form})


@login_required
@role_required('PHARMACIST', 'DOCTOR')
def prescription_status_update(request, pk):
    pres = get_object_or_404(Prescription, pk=pk)
    casefile_id = pres.case_file_id
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Prescription.STATUS_CHOICES):
            pres.status = status
            pres.save(update_fields=['status'])
            CaseActivityLog.objects.create(case_file=pres.case_file, user=request.user, action=f'Prescription status set to {status}')
    return tab_prescriptions(request, casefile_id)


@login_required
@role_required('DOCTOR', 'NURSE')
def medical_history_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = MedicalRecordForm(request.POST)
    if form.is_valid():
        rec = form.save(commit=False)
        rec.mother = case_file.patient
        rec.doctor = request.user
        rec.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Medical history record added')
        return tab_medical_history(request, casefile_id)
    records = MedicalRecord.objects.filter(mother=case_file.patient).order_by('-created_at')[:10]
    return render(request, 'casefiles/tabs/_medical_history.html', {
        'case_file': case_file,
        'patient': case_file.patient,
        'records': records,
        'form': form,
    })


@login_required
@role_required('ADMIN', 'RECEPTIONIST')
def billing_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = CaseBillingRecordForm(request.POST)
    if form.is_valid():
        rec = form.save(commit=False)
        rec.case_file = case_file
        # Compute total if not provided
        if not rec.total_amount:
            rec.total_amount = (rec.consultation_fee or 0) + (rec.lab_charges or 0) + (rec.medication_cost or 0)
        rec.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Billing record added')
        return tab_billing(request, casefile_id)
    invoices = Invoice.objects.filter(patient=case_file.patient).order_by('-created_at')[:50]
    totals = invoices.aggregate(amount=Sum('amount'))
    billing_records = case_file.billing_records.order_by('-created_at')[:50]
    return render(request, 'casefiles/tabs/_billing.html', {
        'case_file': case_file,
        'invoices': invoices,
        'invoices_total': totals.get('amount') or 0,
        'billing_records': billing_records,
        'form': form,
    })


@login_required
@role_required('DOCTOR', 'NURSE')
def baby_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = BabyProfileForm(request.POST)
    if form.is_valid():
        baby = form.save(commit=False)
        baby.mother = case_file.patient
        baby.registered_by = request.user
        baby.save()
        CaseActivityLog.objects.create(case_file=case_file, user=request.user, action='Baby profile added')
        return tab_maternity(request, casefile_id)
    babies = BabyProfile.objects.filter(mother=case_file.patient).order_by('date_of_birth')
    schedules = ImmunizationSchedule.objects.filter(baby__in=babies).order_by('scheduled_date')[:50]
    return render(request, 'casefiles/tabs/_maternity.html', {
        'case_file': case_file,
        'babies': babies,
        'schedules': schedules,
        'form': form,
    })


@login_required
@role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST', 'PHARMACIST', 'LAB_TECH')
def access_log_new(request, casefile_id):
    case_file = get_object_or_404(PatientCaseFile, id=casefile_id)
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    form = CaseActivityLogForm(request.POST)
    if form.is_valid():
        log = form.save(commit=False)
        log.case_file = case_file
        log.user = request.user
        log.save()
        return tab_access(request, casefile_id)
    logs = case_file.activity_logs.order_by('-created_at')[:50]
    return render(request, 'casefiles/tabs/_access.html', {
        'case_file': case_file,
        'logs': logs,
        'form': form,
    })