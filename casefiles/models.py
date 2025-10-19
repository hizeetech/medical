from django.conf import settings
from django.db import models
from django.utils import timezone

from patients.models import MotherProfile
from billing.models import Invoice


class PatientCaseFile(models.Model):
    patient = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='case_files')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_case_files')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_case_files')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    primary_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_doctor_case_files')

    def __str__(self):
        return f"CaseFile #{self.id} - {self.patient.full_name} ({self.patient.member_id})"


class VisitRecord(models.Model):
    case_file = models.ForeignKey(PatientCaseFile, on_delete=models.CASCADE, related_name='visits')
    date_of_visit = models.DateTimeField(default=timezone.now)
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='visit_records')
    complaints = models.TextField()
    examination_findings = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    recommended_tests = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visit {self.date_of_visit:%Y-%m-%d} - {self.case_file.patient.full_name}"


class Prescription(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ISSUED', 'Issued'),
        ('DISPENSED', 'Dispensed'),
    ]
    case_file = models.ForeignKey(PatientCaseFile, on_delete=models.CASCADE, related_name='prescriptions')
    drug_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100, blank=True)
    route = models.CharField(max_length=100, blank=True)
    prescribing_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='prescribed_medications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.drug_name} - {self.case_file.patient.full_name}"


class LabResult(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('REVIEWED', 'Reviewed'),
    ]
    case_file = models.ForeignKey(PatientCaseFile, on_delete=models.CASCADE, related_name='lab_results')
    test_type = models.CharField(max_length=255)
    date_performed = models.DateField(default=timezone.now)
    result_text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='casefiles/lab_results/', blank=True, null=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='performed_lab_results')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.test_type} - {self.case_file.patient.full_name}"


class CaseBillingRecord(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
    ]
    case_file = models.ForeignKey(PatientCaseFile, on_delete=models.CASCADE, related_name='billing_records')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='case_billing_records')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lab_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medication_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Billing #{self.id} - {self.case_file.patient.full_name}"


class CaseAttachment(models.Model):
    case_file = models.ForeignKey(PatientCaseFile, on_delete=models.CASCADE, related_name='attachments')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='casefiles/attachments/')
    attachment_type = models.CharField(max_length=100, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='casefile_attachments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment - {self.title}"


class CaseActivityLog(models.Model):
    case_file = models.ForeignKey(PatientCaseFile, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} - {self.action}"