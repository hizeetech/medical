from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from ckeditor.widgets import CKEditorWidget

from .models import User, FacilityExcelUpload
from .forms import StaffUserAdminAddForm, StaffUserAdminChangeForm
from patients.models import MotherProfile


class MotherProfileInline(admin.StackedInline):
    model = MotherProfile
    can_delete = False
    fk_name = 'user'
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = StaffUserAdminChangeForm
    add_form = StaffUserAdminAddForm

    formfield_overrides = {models.TextField: {'widget': CKEditorWidget}}

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'avatar')}),
        ('Professional info', {'fields': ('specialty', 'sub_specialty', 'treatments_services')}),
        ('Facility IDs', {'fields': ('hospital_clinic_id', 'facility_name', 'staff_id', 'staff_serial_number')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'role',
                'first_name', 'last_name', 'phone_number', 'avatar',
                'specialty', 'sub_specialty', 'treatments_services',
                # Sequential dropdowns (non-patient)
                'state', 'lga_name', 'lga_number', 'facility_type', 'facility_number',
            ),
        }),
    )
    readonly_fields = ('hospital_clinic_id', 'staff_id', 'facility_name')
    list_display = ('email', 'role', 'hospital_clinic_id', 'facility_name', 'staff_id', 'first_name', 'last_name', 'is_staff')
    list_filter = ('role', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'hospital_clinic_id', 'staff_id')
    ordering = ('email',)

    class Media:
        js = (
            # Served from accounts/static/js/... → /static/js/accounts_admin_form.js
            'js/accounts_admin_form.js',
        )

    inlines = [MotherProfileInline]

    def get_inline_instances(self, request, obj=None):
        """Show MotherProfile inline only for patient users.

        When editing staff accounts, the mother profile inline contains required
        fields (e.g., full_name) which should not block saving unrelated changes
        like permissions. By hiding the inline for non-patient roles, we prevent
        validation of mother fields on staff accounts.
        """
        # If there is no object yet (add view), do not show the inline unless
        # the role is explicitly PATIENT, which we cannot know here, so hide it.
        if obj is None:
            return []
        # For existing objects, only show inline for PATIENT role
        if getattr(obj, 'role', None) != 'PATIENT':
            return []
        return super().get_inline_instances(request, obj)


@admin.register(FacilityExcelUpload)
class FacilityExcelUploadAdmin(admin.ModelAdmin):
    list_display = ('uploaded_at', 'file', 'notes')
    ordering = ('-uploaded_at',)
