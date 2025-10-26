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

    # Staff roles routing (with new role groups)
    if role == 'DOCTOR':
        return redirect('doctor_dashboard')
    elif role in ['NURSE', 'CHO', 'CHEW']:
        return redirect('nurse_dashboard')
    elif role in ['RECEPTIONIST', 'HEALTH_RECORD_TECHNICIAN']:
        return redirect('receptionist_dashboard')
    elif role in ['PHARMACIST', 'PHARMACY_TECHNICIAN']:
        return redirect('pharmacist_dashboard')
    elif role in ['LAB_TECH', 'LAB_ATTENDANT']:
        return redirect('lab_tech_dashboard')

    # Fallback: patient dashboard
    from patients.views import dashboard as patient_dashboard
    return patient_dashboard(request)
