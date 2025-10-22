from django.db import models
import uuid
from django.conf import settings


class MotherProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mother_profile')
    member_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    marital_status = models.CharField(max_length=50, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    blood_type = models.CharField(max_length=10, blank=True)
    allergies = models.TextField(blank=True)
    previous_pregnancies = models.TextField(blank=True)
    existing_conditions = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.member_id:
            # Generate a short unique member id
            self.member_id = f"MED-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class BabyProfile(models.Model):
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='babies')
    name = models.CharField(max_length=255)
    hospital_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    apgar_score = models.CharField(max_length=20, blank=True)
    blood_type = models.CharField(max_length=10, blank=True)
    # New: track who registered this baby (doctor/nurse or mother)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.mother.full_name})"

    def save(self, *args, **kwargs):
        if not self.hospital_id:
            self.hospital_id = f"BHB-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class VitalSigns(models.Model):
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='vitals')
    recorded_at = models.DateTimeField(auto_now_add=True)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    pulse = models.IntegerField(null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    def __str__(self):
        return f"Vitals {self.mother.full_name} @ {self.recorded_at}"


class MedicalRecord(models.Model):
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_records')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Record {self.mother.full_name} ({self.created_at:%Y-%m-%d})"


class PostnatalCareRecord(models.Model):
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='postnatal_records')
    created_at = models.DateTimeField(auto_now_add=True)
    wound_care_notes = models.TextField(blank=True)
    emotional_state = models.CharField(max_length=100, blank=True)
    nutrition_notes = models.TextField(blank=True)
    breastfeeding_progress = models.TextField(blank=True)

    def __str__(self):
        return f"Postnatal {self.mother.full_name} ({self.created_at:%Y-%m-%d})"


class DangerSignReport(models.Model):
    SUBJECT_CHOICES = (
        ('MOTHER', 'Mother'),
        ('BABY', 'Baby'),
    )
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('ACK', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    )

    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE, related_name='danger_signs')
    baby = models.ForeignKey(BabyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='danger_signs')
    subject = models.CharField(max_length=10, choices=SUBJECT_CHOICES, default='MOTHER')
    symptoms = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='NEW')
    assigned_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_alerts')
    created_at = models.DateTimeField(auto_now_add=True)
    is_escalated = models.BooleanField(default=False)

    def __str__(self):
        return f"Danger Sign ({self.subject}) for {self.mother.full_name}"


class MedicalRecordAttachment(models.Model):
    TYPE_CHOICES = (
        ('SCAN', 'Scan/Imaging'),
        ('TEST', 'Lab Test'),
        ('PRESCRIPTION', 'Prescription'),
        ('NOTE', 'Clinical Note'),
    )
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='medical_records/')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment ({self.get_type_display()}) for {self.record.mother.full_name}"
