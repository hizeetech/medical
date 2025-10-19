from django import forms
from .models import MotherProfile


class MotherProfileForm(forms.ModelForm):
    class Meta:
        model = MotherProfile
        fields = [
            'full_name', 'age', 'address', 'phone_number', 'marital_status',
            'occupation', 'blood_type', 'allergies', 'previous_pregnancies',
            'existing_conditions', 'emergency_contact', 'profile_picture'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'previous_pregnancies': forms.Textarea(attrs={'rows': 3}),
            'existing_conditions': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()