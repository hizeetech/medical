from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'action_datetime', 'action_type', 'module', 'model', 'object_id',
        'mother_name', 'baby_name', 'vaccine_name', 'scheduled_date', 'completed_date',
        'staff_name', 'staff_id', 'hospital_clinic_id',
    )
    list_filter = ('action_type', 'module', 'model', 'action_date', 'scheduled_date', 'completed_date')
    search_fields = (
        'object_id', 'staff_id', 'hospital_clinic_id', 'staff_name', 'action_description',
        'mother_name', 'mother_member_id', 'baby_name', 'baby_hospital_id', 'vaccine_name'
    )
    ordering = ('-action_datetime',)
    readonly_fields = (
        'action_type', 'module', 'model', 'object_id', 'action_description',
        'user', 'staff_name', 'staff_id', 'hospital_clinic_id',
        'action_datetime', 'action_date', 'action_time',
        'mother_name', 'mother_member_id', 'baby_name', 'baby_hospital_id',
        'vaccine_name', 'scheduled_date', 'completed_date',
    )

    def has_view_permission(self, request, obj=None):
        # Only allow superusers or users with explicit permission to view
        return bool(request.user and (request.user.is_superuser or request.user.has_perm('audit.view_activitylog')))

    def has_module_permission(self, request):
        return self.has_view_permission(request)