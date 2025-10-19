from django.db import models
from django.conf import settings
from patients.models import MotherProfile

class Invoice(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )
    patient = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='invoices')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice {self.reference} - {self.patient.full_name}"


class PaymentRecord(models.Model):
    GATEWAY_CHOICES = (
        ('PAYSTACK', 'Paystack'),
        ('FLUTTERWAVE', 'Flutterwave'),
        ('OPAY', 'Opay'),
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    provider_reference = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='PENDING')
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.gateway} for {self.invoice.reference}"