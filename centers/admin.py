from django.contrib import admin
from django.db import models
from ckeditor.widgets import CKEditorWidget
from .models import Center, DoctorSchedule


class RichTextAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}

@admin.register(Center)
class CenterAdmin(RichTextAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("related_doctors",)


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(RichTextAdmin):
    list_display = ("center", "doctor", "day_of_week", "start_time", "end_time")
    list_filter = ("center", "day_of_week")
    search_fields = ("center__name", "doctor__email")