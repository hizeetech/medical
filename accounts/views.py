from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Role-aware dashboard router
@login_required
def dashboard_router(request):
    user = request.user
    role = getattr(user, 'role', 'PATIENT') or 'PATIENT'

    # Patients see the existing patient dashboard
    if role == 'PATIENT' and not (user.is_staff or user.is_superuser):
        from patients.views import dashboard as patient_dashboard
        return patient_dashboard(request)

    # Admins go to admin dashboard
    if user.is_superuser or role == 'ADMIN':
        return redirect('admin_dashboard')

    # Staff roles routing
    role_to_route = {
        'DOCTOR': 'doctor_dashboard',
        'NURSE': 'nurse_dashboard',
        'RECEPTIONIST': 'receptionist_dashboard',
        'PHARMACIST': 'pharmacist_dashboard',
        'LAB_TECH': 'lab_tech_dashboard',
    }
    target = role_to_route.get(role)
    if target:
        return redirect(target)

    # Fallback: patient dashboard
    from patients.views import dashboard as patient_dashboard
    return patient_dashboard(request)
