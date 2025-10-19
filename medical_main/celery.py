import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_main.settings')

app = Celery('medical_main')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Default beat schedule: daily reminders at 08:00 and 08:30 UTC
app.conf.beat_schedule = {
    'daily-immunization-reminders': {
        'task': 'notifications.tasks.send_daily_immunization_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    'daily-appointment-reminders': {
        'task': 'notifications.tasks.send_daily_appointment_reminders',
        'schedule': crontab(hour=8, minute=30),
    },
}