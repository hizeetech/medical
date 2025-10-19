from django.db import models
from django.conf import settings


class NotificationLog(models.Model):
    CHANNEL_CHOICES = (
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('IN_APP', 'In-App'),
    )
    TYPE_CHOICES = (
        ('APPOINTMENT', 'Appointment'),
        ('REMINDER', 'Reminder'),
        ('HEALTH_ALERT', 'Health Alert'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.type} via {self.channel} to {self.recipient.email}"
