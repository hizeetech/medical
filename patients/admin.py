from django.contrib import admin
from django.db import models
from ckeditor.widgets import CKEditorWidget
from .models import (
    MotherProfile,
    BabyProfile,
    VitalSigns,
    MedicalRecord,
    PostnatalCareRecord,
    DangerSignReport,
    MedicalRecordAttachment
)


class RichTextAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}

@admin.register(MotherProfile)
class MotherProfileAdmin(RichTextAdmin):
    list_display = ('full_name', 'member_id', 'phone_number', 'marital_status', 'created_at')
    search_fields = ('full_name', 'phone_number')


@admin.register(BabyProfile)
class BabyProfileAdmin(RichTextAdmin):
    list_display = ('name', 'mother', 'date_of_birth', 'gender', 'registered_by')
    search_fields = ('name', 'mother__full_name', 'registered_by__email')


@admin.register(VitalSigns)
class VitalSignsAdmin(RichTextAdmin):
    list_display = ('mother', 'recorded_at', 'blood_pressure_systolic', 'pulse')
    list_filter = ('recorded_at',)


@admin.register(MedicalRecord)
class MedicalRecordAdmin(RichTextAdmin):
    list_display = ('mother', 'doctor', 'created_at')
    search_fields = ('mother__full_name', 'doctor__email')


@admin.register(PostnatalCareRecord)
class PostnatalCareRecordAdmin(RichTextAdmin):
    list_display = ('mother', 'created_at', 'emotional_state')


@admin.register(DangerSignReport)
class DangerSignReportAdmin(RichTextAdmin):
    list_display = ('mother', 'subject', 'status', 'is_escalated', 'created_at')
    list_filter = ('subject', 'status', 'is_escalated')


@admin.register(MedicalRecordAttachment)
class MedicalRecordAttachmentAdmin(RichTextAdmin):
    list_display = ('record', 'type', 'uploaded_at')
    search_fields = ('record__mother__full_name',)
