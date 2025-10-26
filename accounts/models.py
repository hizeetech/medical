from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, max_length=255)

    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('DOCTOR', 'Doctor'),
        ('NURSE', 'Nurse'),
        ('PATIENT', 'Patient'),
        ('RECEPTIONIST', 'Receptionist'),
        ('PHARMACIST', 'Pharmacist'),
        ('LAB_TECH', 'Lab Technician'),
        # Newly Added Roles (kept uppercase to match existing usage)
        ('CHO', 'Community Health Officer (CHO)'),
        ('CHEW', 'Community Health Extension Worker (CHEW)'),
        ('LAB_ATTENDANT', 'Lab Attendant'),
        ('PHARMACY_TECHNICIAN', 'Pharmacy Technician'),
        ('HEALTH_RECORD_TECHNICIAN', 'Health Record Technician'),
    )
    role = models.CharField(max_length=255, choices=ROLE_CHOICES, default='PATIENT')
    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # IDs auto-generated for non-patient staff
    hospital_clinic_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    staff_id = models.CharField(max_length=80, blank=True, null=True, unique=True)
    staff_serial_number = models.PositiveIntegerField(blank=True, null=True)
    facility_name = models.CharField(max_length=255, blank=True, null=True)

    #Additional Fields for Doctors
    specialty = models.TextField(blank=True, null=True)
    sub_specialty = models.TextField(blank=True, null=True)

    #Additional Fields for Treatments and services
    treatments_services = models.TextField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class FacilityExcelUpload(models.Model):
    file = models.FileField(upload_to='facility_excel/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Excel uploaded at {self.uploaded_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Facility Excel ({self.uploaded_at:%Y-%m-%d %H:%M})"
