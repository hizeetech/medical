from django.contrib import admin
from accounts.admin import UserAdmin as BaseUserAdmin
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(BaseUserAdmin):
    # Show only users that look like doctors (have any professional detail)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(specialty__isnull=True).exclude(specialty="")

    # Minor label tweak for clarity in the changelist
    def get_changelist(self, request):
        return super().get_changelist(request)

    # Optional: you could override fieldsets to emphasize doctor fields
    # but we reuse BaseUserAdmin to keep forms consistent.

# Register your models here.
