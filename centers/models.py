from django.db import models
from django.conf import settings


class Center(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    short_description = models.TextField(blank=True)

    # Image uploads stored in MEDIA_ROOT
    hero_image = models.ImageField(upload_to='centers/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='centers/', blank=True, null=True)
    image = models.ImageField(upload_to='centers/', blank=True, null=True)

    # Content sections (kept simple for now)
    overview = models.TextField(blank=True)
    services_offered = models.TextField(blank=True)
    conditions_treated = models.TextField(blank=True)
    contact_details = models.TextField(blank=True)

    # Assign doctors to a center
    related_doctors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='assigned_centers'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DoctorSchedule(models.Model):
    DAYS = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='schedules')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_schedules')
    day_of_week = models.CharField(max_length=16, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['center', 'doctor', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor} @ {self.center} on {self.day_of_week} {self.start_time}-{self.end_time}"