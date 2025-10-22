from django.contrib import admin

from .models import (
    PatientCaseFile,
    VisitRecord,
    Prescription,
    LabResult,
    CaseBillingRecord,
    CaseAttachment,
    CaseActivityLog,
    BabyCaseFile,
    BabyVisitRecord,
    BabyPrescription,
    BabyLabResult,
    BabyCaseBillingRecord,
    BabyCaseAttachment,
    BabyCaseActivityLog,
)


@admin.register(PatientCaseFile)
class PatientCaseFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'created_by', 'created_at', 'updated_at')
    search_fields = ('patient__full_name', 'patient__member_id')
    list_filter = ('created_at',)


@admin.register(VisitRecord)
class VisitRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'date_of_visit', 'provider')
    search_fields = ('case_file__patient__full_name', 'provider__email')
    list_filter = ('date_of_visit',)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'drug_name', 'status', 'prescribing_by', 'created_at')
    search_fields = ('drug_name', 'case_file__patient__full_name')
    list_filter = ('status',)


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'test_type', 'status', 'performed_by', 'date_performed')
    search_fields = ('test_type', 'case_file__patient__full_name')
    list_filter = ('status',)


@admin.register(CaseBillingRecord)
class CaseBillingRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'invoice', 'total_amount', 'payment_status')
    list_filter = ('payment_status',)


@admin.register(CaseAttachment)
class CaseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'title', 'uploaded_by', 'created_at')


@admin.register(CaseActivityLog)
class CaseActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'user', 'action', 'created_at')


@admin.register(BabyCaseFile)
class BabyCaseFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'baby', 'created_by', 'created_at', 'updated_at')
    search_fields = ('baby__name', 'baby__hospital_id', 'baby__mother__member_id')
    list_filter = ('created_at',)


@admin.register(BabyVisitRecord)
class BabyVisitRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'date_of_visit', 'provider')
    search_fields = ('case_file__baby__name', 'provider__email')
    list_filter = ('date_of_visit',)


@admin.register(BabyPrescription)
class BabyPrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'drug_name', 'status', 'prescribing_by', 'created_at')
    search_fields = ('drug_name', 'case_file__baby__name')
    list_filter = ('status',)


@admin.register(BabyLabResult)
class BabyLabResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'test_type', 'status', 'performed_by', 'date_performed')
    search_fields = ('test_type', 'case_file__baby__name')
    list_filter = ('status',)


@admin.register(BabyCaseBillingRecord)
class BabyCaseBillingRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'invoice', 'total_amount', 'payment_status')
    list_filter = ('payment_status',)


@admin.register(BabyCaseAttachment)
class BabyCaseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'title', 'uploaded_by', 'created_at')


@admin.register(BabyCaseActivityLog)
class BabyCaseActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'case_file', 'user', 'action', 'created_at')