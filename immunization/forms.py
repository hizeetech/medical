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