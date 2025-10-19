from django.contrib import admin
from django.db import models
from ckeditor.widgets import CKEditorWidget
from .models import ImmunizationSchedule, ImmunizationMaster


class RichTextAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}

@admin.register(ImmunizationMaster)
class ImmunizationMasterAdmin(RichTextAdmin):
    list_display = ('name', 'interval_value', 'interval_unit', 'is_active')
    list_filter = ('interval_unit', 'is_active')
    search_fields = ('name',)

@admin.register(ImmunizationSchedule)
class ImmunizationScheduleAdmin(RichTextAdmin):
    list_display = ('baby', 'vaccine_name', 'scheduled_date', 'status', 'date_completed')
    list_filter = ('status', 'scheduled_date')
    search_fields = ('baby__name', 'vaccine_name')
