from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from patients.models import MotherProfile
from .models import Invoice

@login_required
def invoice_list(request):
    # Show only the current user's invoices unless staff
    if request.user.is_staff or request.user.is_superuser:
        invoices = Invoice.objects.select_related('patient').order_by('-created_at')
    else:
        try:
            profile = MotherProfile.objects.get(user=request.user)
            invoices = Invoice.objects.select_related('patient').filter(patient=profile).order_by('-created_at')
        except MotherProfile.DoesNotExist:
            invoices = Invoice.objects.none()
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})

@login_required
def invoice_new(request, patient_id):
    try:
        patient = MotherProfile.objects.get(pk=patient_id)
    except MotherProfile.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('invoice_list')

    if request.method == 'POST':
        description = request.POST.get('description') or 'Consultation'
        amount = request.POST.get('amount')
        if not amount:
            messages.error(request, 'Amount is required')
            return redirect('invoice_new', patient_id=patient_id)
        reference = f"INV-{get_random_string(10).upper()}"
        invoice = Invoice.objects.create(
            patient=patient,
            created_by=request.user,
            reference=reference,
            description=description,
            amount=amount,
            status='PENDING',
        )
        messages.success(request, f'Invoice {invoice.reference} created')
        return redirect('invoice_list')

    return render(request, 'billing/invoice_new.html', {'patient': patient})