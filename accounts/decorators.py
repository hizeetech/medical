from functools import wraps
from django.http import HttpResponseForbidden


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return HttpResponseForbidden("Authentication required")
            # Admin always allowed
            if user.is_superuser or user.role == 'ADMIN':
                return view_func(request, *args, **kwargs)
            if allowed_roles and user.role not in allowed_roles:
                return HttpResponseForbidden("You do not have permission to access this resource")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator