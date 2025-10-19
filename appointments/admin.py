from django.contrib import admin
from django.db import models
from ckeditor.widgets import CKEditorWidget
from .models import Appointment


class RichTextAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}

@admin.register(Appointment)
class AppointmentAdmin(RichTextAdmin):
    list_display = ('patient', 'doctor', 'appointment_type', 'scheduled_at', 'status')
    list_filter = ('appointment_type', 'status', 'scheduled_at')
    search_fields = ('patient__full_name', 'doctor__email')
