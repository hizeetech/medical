from django.contrib import admin
from .models import Invoice, PaymentRecord

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('reference', 'patient', 'amount', 'status', 'created_at')
    search_fields = ('reference', 'patient__full_name')
    list_filter = ('status', 'created_at')

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'gateway', 'amount', 'status', 'created_at')
    list_filter = ('gateway', 'status')