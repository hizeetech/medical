from django.db import models
from django.conf import settings
from patients.models import BabyProfile

# Use the project user model
USER_MODEL = settings.AUTH_USER_MODEL


# Admin-configurable master list of immunizations
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
        ('DUE', 'Pending'),  # display "Pending" for patient-facing UI
        ('DONE', 'Done'),
        ('MISSED', 'Missed'),
    )

    baby = models.ForeignKey(BabyProfile, on_delete=models.CASCADE, related_name='immunizations')
    vaccine_name = models.CharField(max_length=100)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DUE')
    notes = models.TextField(blank=True)
    # Record the actual date when the vaccine was administered
    date_completed = models.DateField(blank=True, null=True)

    # Workflow fields
    visible_to_mother = models.BooleanField(default=False)
    approved_by = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_immunizations')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Administration details
    administered_by = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='administered_immunizations')
    administered_at = models.DateTimeField(null=True, blank=True)
    batch_number = models.CharField(max_length=120, blank=True)
    manufacturer = models.CharField(max_length=120, blank=True)
    administration_site = models.CharField(max_length=64, blank=True, help_text='e.g., Left Arm, Right Thigh')
    post_observation_notes = models.TextField(blank=True)

    # Rescheduling support
    rescheduled_for = models.DateField(null=True, blank=True)
    reschedule_reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.vaccine_name} for {self.baby.name} ({self.scheduled_date})"


class ImmunizationApproval(models.Model):
    baby = models.OneToOneField(BabyProfile, on_delete=models.CASCADE, related_name='immunization_approval')
    approved_by = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='immunization_approvals')
    approved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Approval for {self.baby.name}"


class VaccinationEventLog(models.Model):
    EVENT_CHOICES = (
        ('ADMINISTERED', 'Administered'),
        ('OBSERVATION_ADDED', 'Observation Added'),
        ('RESCHEDULED', 'Rescheduled'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('APPROVED', 'Approved'),
        ('CERTIFICATE_GENERATED', 'Certificate Generated'),
    )
    schedule = models.ForeignKey(ImmunizationSchedule, on_delete=models.CASCADE, related_name='event_logs')
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    performed_by = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='vaccination_events')
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.event_type} • {self.schedule.vaccine_name} • {self.timestamp:%Y-%m-%d}"


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    changed_by = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, default='WEB')

    def __str__(self):
        return f"{self.model_name} {self.action} ({self.timestamp:%Y-%m-%d})"


class ImmunizationRuleConfig(models.Model):
    reschedule_window_days = models.IntegerField(default=30)
    pre_due_reminder_days = models.IntegerField(default=3)
    observation_reminder_hours = models.IntegerField(default=24)
    missed_after_days = models.IntegerField(default=2)
    hospital_name = models.CharField(max_length=200, default='Medical Care Hospital')
    certificate_footer_note = models.TextField(blank=True)

    def __str__(self):
        return 'Immunization Rules'


class ImmunizationCertificate(models.Model):
    baby = models.OneToOneField(BabyProfile, on_delete=models.CASCADE, related_name='immunization_certificate')
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='certificates/', blank=True)
    data_snapshot = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Certificate — {self.baby.name}"
