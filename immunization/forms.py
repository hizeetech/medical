from django import forms
from .models import ImmunizationMaster


class AddBabyImmunizationForm(forms.Form):
    master = forms.ModelChoiceField(
        queryset=ImmunizationMaster.objects.filter(is_active=True),
        label='Immunization'
    )
    scheduled_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2})
    )


class AdministerImmunizationForm(forms.Form):
    batch_number = forms.CharField(required=False, max_length=120)
    manufacturer = forms.CharField(required=False, max_length=120)
    administration_site = forms.CharField(required=False, max_length=64)
    administered_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))


class ObservationForm(forms.Form):
    notes = forms.CharField(required=True, widget=forms.Textarea(attrs={'rows': 3}))


class RescheduleForm(forms.Form):
    rescheduled_for = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    reason = forms.CharField(required=False, max_length=200)