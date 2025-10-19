from django.contrib import admin
from django.db import models
from ckeditor.widgets import CKEditorWidget
from .models import NotificationLog
from django.urls import path
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages
from .utils import send_sms, send_email


class RichTextAdmin(admin.ModelAdmin):
    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}

@admin.register(NotificationLog)
class NotificationLogAdmin(RichTextAdmin):
    list_display = ('recipient', 'type', 'channel', 'sent_at', 'success')
    list_filter = ('type', 'channel', 'success', 'sent_at')
    search_fields = ('recipient__email', 'message')
    change_list_template = 'admin/notifications_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('test-sms/', self.admin_site.admin_view(self.test_sms_view), name='notifications_test_sms'),
            path('test-email/', self.admin_site.admin_view(self.test_email_view), name='notifications_test_email'),
        ]
        return custom + urls

    class TestSMSForm(forms.Form):
        to_number = forms.CharField(label="Recipient phone", max_length=20)
        message = forms.CharField(label="Message", widget=forms.Textarea, initial="Test SMS from admin")

    class TestEmailForm(forms.Form):
        to_email = forms.EmailField(label="Recipient email")
        subject = forms.CharField(label="Subject", initial="Test Email")
        message = forms.CharField(label="Message", widget=forms.Textarea, initial="Test email from admin")

    def test_sms_view(self, request):
        form = self.TestSMSForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            to = form.cleaned_data['to_number']
            msg = form.cleaned_data['message']
            ok, meta = send_sms(to, msg)
            try:
                NotificationLog.objects.create(
                    recipient=request.user,
                    channel='SMS',
                    type='HEALTH_ALERT',
                    message=msg,
                    success=ok,
                    meta=meta,
                )
            except Exception:
                pass
            if ok:
                messages.success(request, 'SMS sent successfully.')
            else:
                messages.error(request, 'SMS failed. See NotificationLog meta for details.')
            return redirect('admin:notifications_test_sms')
        context = {'form': form, 'title': 'Test SMS (EbulkSMS)'}
        return render(request, 'admin/test_sms.html', context)

    def test_email_view(self, request):
        form = self.TestEmailForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            to = form.cleaned_data['to_email']
            subject = form.cleaned_data['subject']
            msg = form.cleaned_data['message']
            ok_email = send_email(to, subject, msg, text_content=msg)
            try:
                NotificationLog.objects.create(
                    recipient=request.user,
                    channel='EMAIL',
                    type='HEALTH_ALERT',
                    message=subject,
                    success=ok_email,
                    meta={'backend': getattr(request, 'EMAIL_BACKEND', None) or 'smtp'},
                )
            except Exception:
                pass
            if ok_email:
                messages.success(request, 'Email sent successfully.')
            else:
                messages.error(request, 'Email failed. Check email backend configuration.')
            return redirect('admin:notifications_test_email')
        context = {'form': form, 'title': 'Test Email'}
        return render(request, 'admin/test_email.html', context)
