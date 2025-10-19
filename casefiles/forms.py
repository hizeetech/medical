from django import forms

from .models import VisitRecord, Prescription, LabResult, CaseAttachment, CaseBillingRecord, CaseActivityLog
from patients.models import MedicalRecord, BabyProfile
from billing.models import Invoice


class VisitRecordForm(forms.ModelForm):
    class Meta:
        model = VisitRecord
        fields = [
            'complaints', 'examination_findings', 'diagnosis',
            'recommended_tests', 'treatment_plan'
        ]
        widgets = {
            'complaints': forms.Textarea(attrs={'rows': 3}),
            'examination_findings': forms.Textarea(attrs={'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'recommended_tests': forms.Textarea(attrs={'rows': 2}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
        }


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['drug_name', 'dosage', 'frequency', 'duration', 'route', 'status']


class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['test_type', 'date_performed', 'result_text', 'attachment', 'status']
        widgets = {
            'result_text': forms.Textarea(attrs={'rows': 3}),
            'attachment': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }


class CaseAttachmentForm(forms.ModelForm):
    class Meta:
        model = CaseAttachment
        fields = ['title', 'attachment_type', 'file']
        widgets = {
            'title': forms.Textarea(attrs={'rows': 3}),
            'file': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }


class CaseBillingRecordForm(forms.ModelForm):
    invoice = forms.ModelChoiceField(queryset=Invoice.objects.all(), required=False)

    class Meta:
        model = CaseBillingRecord
        fields = ['invoice', 'consultation_fee', 'lab_charges', 'medication_cost', 'total_amount', 'payment_status']
        widgets = {
            'consultation_fee': forms.NumberInput(attrs={'step': '0.01'}),
            'lab_charges': forms.NumberInput(attrs={'step': '0.01'}),
            'medication_cost': forms.NumberInput(attrs={'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'step': '0.01'}),
        }


class BabyProfileForm(forms.ModelForm):
    class Meta:
        model = BabyProfile
        fields = ['name', 'gender', 'date_of_birth', 'weight_kg', 'height_cm', 'apgar_score', 'blood_type']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }


class CaseActivityLogForm(forms.ModelForm):
    class Meta:
        model = CaseActivityLog
        fields = ['action', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }