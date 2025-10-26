from typing import Any, Dict

from django import forms
from django.db.models import Max
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import User
from .utils import (
    STATE_CHOICES,
    LGA_NUMBER_CHOICES,
    FACILITY_TYPE_CHOICES,
    FACILITY_NUMBER_CHOICES,
    get_facility_data,
    make_hospital_clinic_id,
    find_facility_name,
    parse_hospital_clinic_id,
)


class StaffUserAdminAddForm(UserCreationForm):
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False)
    lga_name = forms.ChoiceField(choices=[], required=False)
    lga_number = forms.ChoiceField(choices=LGA_NUMBER_CHOICES, required=False)
    facility_type = forms.ChoiceField(choices=FACILITY_TYPE_CHOICES, required=False)
    facility_number = forms.ChoiceField(choices=FACILITY_NUMBER_CHOICES, required=False)

    class Meta:
        model = User
        fields = (
            'email', 'role', 'first_name', 'last_name', 'phone_number', 'avatar',
            'specialty', 'sub_specialty', 'treatments_services',
            # virtual dropdowns for non-patient
            'state', 'lga_name', 'lga_number', 'facility_type', 'facility_number',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = get_facility_data()
        self.fields['lga_name'].choices = data.get('lga_choices', [])  # type: ignore
        # Disable sequential until prior selected
        self.fields['lga_name'].widget.attrs['disabled'] = True
        self.fields['lga_number'].widget.attrs['disabled'] = True
        self.fields['facility_type'].widget.attrs['disabled'] = True
        self.fields['facility_number'].widget.attrs['disabled'] = True
        # Add hooks for JS
        for name in ('state','lga_name','lga_number','facility_type','facility_number','role'):
            self.fields[name].widget.attrs['data-admin-seq'] = '1'

    def clean(self) -> Dict[str, Any]:
        cleaned = super().clean()
        role = cleaned.get('role') or 'PATIENT'
        if role != 'PATIENT':
            state = cleaned.get('state') or 'OGS'
            lga_name = cleaned.get('lga_name')
            lga_number = cleaned.get('lga_number')
            facility_type = cleaned.get('facility_type')
            facility_number = cleaned.get('facility_number')
            missing = [
                name for name, val in (
                    ('lga_name', lga_name),
                    ('lga_number', lga_number),
                    ('facility_type', facility_type),
                    ('facility_number', facility_number),
                ) if not val
            ]
            if missing:
                for f in missing:
                    self.add_error(f, 'Required for non-patient roles.')
                return cleaned
            hospital_id = make_hospital_clinic_id(state, lga_name, lga_number, str(facility_type), str(facility_number))
            cleaned['hospital_clinic_id'] = hospital_id
            # Compute staff serial number and staff_id
            if hospital_id:
                max_serial = User.objects.filter(hospital_clinic_id=hospital_id).aggregate(Max('staff_serial_number'))['staff_serial_number__max'] or 0
                next_serial = max_serial + 1
                cleaned['staff_serial_number'] = next_serial
                cleaned['staff_id'] = f"{hospital_id}/{next_serial:05d}"
            # Resolve facility name from Excel
            facility_name = find_facility_name(str(lga_name), str(lga_number), str(facility_type), str(facility_number))
            cleaned['facility_name'] = facility_name
        else:
            # Ensure staff fields are cleared for patient
            cleaned['hospital_clinic_id'] = None
            cleaned['staff_serial_number'] = None
            cleaned['staff_id'] = None
        return cleaned

    def save(self, commit: bool = True) -> User:
        """Persist computed IDs into the User instance when saving from admin add form."""
        user = super().save(commit=False)
        cleaned = getattr(self, 'cleaned_data', {})
        role = cleaned.get('role') or getattr(user, 'role', 'PATIENT')
        if role != 'PATIENT':
            hospital_id = cleaned.get('hospital_clinic_id')
            serial = cleaned.get('staff_serial_number')
            staff_id = cleaned.get('staff_id')
            # If for any reason serial/staff_id missing, recompute defensively
            if hospital_id and not serial:
                max_serial = User.objects.filter(hospital_clinic_id=hospital_id).aggregate(Max('staff_serial_number'))['staff_serial_number__max'] or 0
                serial = max_serial + 1
                staff_id = f"{hospital_id}/{serial:05d}"
            user.hospital_clinic_id = hospital_id
            user.staff_serial_number = serial
            user.staff_id = staff_id
            user.facility_name = cleaned.get('facility_name')
        else:
            user.hospital_clinic_id = None
            user.staff_serial_number = None
            user.staff_id = None
            user.facility_name = None
        # Ensure role persists (not part of UserCreationForm base fields)
        if 'role' in cleaned:
            user.role = cleaned['role']
        if commit:
            user.save()
            self.save_m2m()
        return user


class StaffUserAdminChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role') or getattr(self.instance, 'role', None)
        if role == 'PATIENT':
            cleaned['facility_name'] = None
            cleaned['staff_id'] = None
            cleaned['hospital_clinic_id'] = None
            return cleaned

        # Recompute facility_name based on hospital_clinic_id components (using LGA abbr)
        hospital_id = cleaned.get('hospital_clinic_id') or getattr(self.instance, 'hospital_clinic_id', '')
        serial = cleaned.get('staff_serial_number') if 'staff_serial_number' in cleaned else getattr(self.instance, 'staff_serial_number', None)

        parsed = parse_hospital_clinic_id(hospital_id or '')
        if parsed:
            state_code, lga_abbr, lga_number, facility_type, facility_number = parsed
            facility_name = find_facility_name(lga_number=lga_number, facility_type=facility_type, facility_number=facility_number, lga_abbr=lga_abbr)
            cleaned['facility_name'] = facility_name
        else:
            # if hospital id malformed, do not alter facility_name here
            pass

        # Validate serial numeric
        if serial is not None:
            try:
                int(serial)
            except Exception:
                raise ValidationError('Staff serial number must be numeric.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        cleaned = self.cleaned_data
        role = cleaned.get('role') or getattr(instance, 'role', None)

        if role == 'PATIENT':
            instance.hospital_clinic_id = None
            instance.staff_id = None
            instance.facility_name = None
        else:
            # Set facility_name from cleaned
            if 'facility_name' in cleaned:
                instance.facility_name = cleaned.get('facility_name')
            # Recompute staff_id when serial changes
            hospital_id = cleaned.get('hospital_clinic_id') or instance.hospital_clinic_id
            serial = cleaned.get('staff_serial_number') if 'staff_serial_number' in cleaned else instance.staff_serial_number
            if hospital_id and serial is not None:
                try:
                    serial_int = int(serial)
                    instance.staff_id = f"{hospital_id}/{serial_int:05d}"
                except Exception:
                    # keep previous staff_id if serial invalid (should be caught in clean)
                    pass
        if commit:
            instance.save()
        return instance