from django.db import models
from patients.models import MotherProfile
from django.conf import settings


class Appointment(models.Model):
    TYPE_CHOICES = (
        ('ANTENATAL', 'Antenatal'),
        ('POSTNATAL', 'Postnatal'),
        ('IMMUNIZATION', 'Immunization'),
    )
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('MISSED', 'Missed'),
    )

    patient = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.appointment_type} on {self.scheduled_at:%Y-%m-%d %H:%M} for {self.patient.full_name}"
