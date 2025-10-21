from django.db import models
from patients.models import BabyProfile


# New: Admin-configurable master list of immunizations
class ImmunizationMaster(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    interval_value = models.PositiveIntegerField(help_text="Number of days/weeks/months after birth")
    interval_unit = models.CharField(max_length=10, choices=[('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')])
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ImmunizationSchedule(models.Model):
    STATUS_CHOICES = (
        ('DUE', 'Pending'),
        ('DONE', 'Done'),
        ('MISSED', 'Missed'),
    )

    baby = models.ForeignKey(BabyProfile, on_delete=models.CASCADE, related_name='immunizations')
    vaccine_name = models.CharField(max_length=100)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DUE')
    notes = models.TextField(blank=True)
    # New: record the actual date when the vaccine was administered
    date_completed = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.vaccine_name} for {self.baby.name} ({self.scheduled_date})"
