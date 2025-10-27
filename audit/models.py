from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('complete', 'Complete'),
    ]

    action_type = models.CharField(max_length=16, choices=ACTION_CHOICES)
    module = models.CharField(max_length=64, help_text='App label where the action occurred')
    model = models.CharField(max_length=64, help_text='Model name affected')
    action_description = models.TextField(blank=True, null=True)

    # Generic relation to the affected object
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    object_id = models.CharField(max_length=64, blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Staff/user context
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, blank=True, null=True, related_name='activity_logs')
    staff_name = models.CharField(max_length=255, blank=True, null=True)
    staff_id = models.CharField(max_length=255, blank=True, null=True)
    hospital_clinic_id = models.CharField(max_length=255, blank=True, null=True)

    # Domain snapshot fields (optional, denormalized for reporting)
    mother_name = models.CharField(max_length=255, blank=True, null=True)
    mother_member_id = models.CharField(max_length=64, blank=True, null=True)
    baby_name = models.CharField(max_length=255, blank=True, null=True)
    baby_hospital_id = models.CharField(max_length=64, blank=True, null=True)
    vaccine_name = models.CharField(max_length=120, blank=True, null=True)
    scheduled_date = models.DateField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)

    # Timestamp (store both for admin filtering convenience)
    action_datetime = models.DateTimeField()
    action_date = models.DateField()
    action_time = models.TimeField()

    class Meta:
        ordering = ('-action_datetime',)
        indexes = [
            models.Index(fields=['module', 'model', 'action_type', 'action_date']),
            models.Index(fields=['staff_id', 'hospital_clinic_id', 'action_date']),
            models.Index(fields=['mother_member_id', 'baby_hospital_id', 'scheduled_date']),
        ]

    def __str__(self):
        return f"{self.action_type} {self.module}.{self.model} #{self.object_id} by {self.staff_id or self.user_id}"