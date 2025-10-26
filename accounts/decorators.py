from functools import wraps
from django.http import HttpResponseForbidden


# Map base roles to equivalent roles that share access
ROLE_EQUIVALENTS = {
    'ADMIN': {'ADMIN'},
    'DOCTOR': {'DOCTOR'},
    'NURSE': {'NURSE', 'CHO', 'CHEW'},
    'RECEPTIONIST': {'RECEPTIONIST', 'HEALTH_RECORD_TECHNICIAN'},
    'PHARMACIST': {'PHARMACIST', 'PHARMACY_TECHNICIAN'},
    'LAB_TECH': {'LAB_TECH', 'LAB_ATTENDANT'},
    'PATIENT': {'PATIENT'},
}


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return HttpResponseForbidden("Authentication required")
            # Admin always allowed
            if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
                return view_func(request, *args, **kwargs)
            # Expand allowed roles to include equivalents
            expanded = set()
            for r in allowed_roles:
                expanded |= ROLE_EQUIVALENTS.get(r, {r})
            if expanded and getattr(user, 'role', None) not in expanded:
                return HttpResponseForbidden("You do not have permission to access this resource")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator