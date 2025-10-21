import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_main.settings')

app = Celery('medical_main')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Default beat schedule: granular immunization reminders and housekeeping
app.conf.beat_schedule = {
    'daily-immunization-pre3': {
        'task': 'notifications.tasks.send_daily_immunization_pre3',
        'schedule': crontab(hour=8, minute=0),
    },
    'daily-immunization-today': {
        'task': 'notifications.tasks.send_daily_immunization_today',
        'schedule': crontab(hour=8, minute=10),
    },
    'daily-immunization-missed2': {
        'task': 'notifications.tasks.send_daily_immunization_missed2',
        'schedule': crontab(hour=8, minute=20),
    },
    'daily-appointment-reminders': {
        'task': 'notifications.tasks.send_daily_appointment_reminders',
        'schedule': crontab(hour=8, minute=30),
    },
    'mark-overdue-immunizations-missed': {
        'task': 'notifications.tasks.mark_overdue_immunizations_missed',
        'schedule': crontab(hour=0, minute=15),
    },
}