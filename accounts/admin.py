from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number', 'avatar')}),
        ('Professional info', {'fields': ('specialty', 'sub_specialty', 'treatments_services')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2', 'role',
                'first_name', 'last_name', 'phone_number',
                'avatar', 'specialty', 'sub_specialty', 'treatments_services'
            ),
        }),
    )
    list_display = ('email', 'role', 'first_name', 'last_name', 'specialty', 'sub_specialty', 'is_staff')
    list_filter = ('role', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'specialty', 'sub_specialty')
    ordering = ('email',)
