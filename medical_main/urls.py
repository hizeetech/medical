"""
URL configuration for medical_main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import home, antenatal_care, postnatal_care, newborn_immunization, find_doctor, articles
from accounts.views import dashboard_router
from patients.views import (
    profile_edit, profile_complete, member_card_pdf,
    record_vitals, postnatal_plan, baby_profile_view,
)
from appointments.views import appointments_list, appointment_new
from immunization.views import schedule_view as immunization_schedule, update_schedule_status, schedule_all_view
from immunization.views import manage_baby_immunizations, baby_immunization_pdf
from centers.views import centers_list, center_detail
from admin_dashboard.views import (
    index as admin_dashboard_index,
    export_appointments_csv,
    export_immunizations_csv,
    nurse_dashboard,
    receptionist_dashboard,
    pharmacist_dashboard,
    lab_tech_dashboard,
)
from doctors.views import dashboard as doctor_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', home, name='home'),
    path('dashboard/', dashboard_router, name='dashboard'),
    path('dashboard/doctor/', doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/nurse/', nurse_dashboard, name='nurse_dashboard'),
    path('dashboard/receptionist/', receptionist_dashboard, name='receptionist_dashboard'),
    path('dashboard/pharmacist/', pharmacist_dashboard, name='pharmacist_dashboard'),
    path('dashboard/lab-tech/', lab_tech_dashboard, name='lab_tech_dashboard'),
    path('profile/', profile_edit, name='profile_edit'),
    path('profile/complete/', profile_complete, name='profile_complete'),
    path('member-card/', member_card_pdf, name='member_card'),
    # Services
    path('appointments/', appointments_list, name='appointments_list'),
    path('appointments/new/', appointment_new, name='appointment_new'),
    path('vitals/', record_vitals, name='record_vitals'),
    path('postnatal-plan/', postnatal_plan, name='postnatal_plan'),
    path('immunization/schedule/', immunization_schedule, name='immunization_schedule'),
    path('immunization/schedule/all/', schedule_all_view, name='immunization_schedule_all'),
    path('immunization/schedule/<int:pk>/status/', update_schedule_status, name='immunization_update_status'),
    path('immunization/baby/<int:baby_id>/manage/', manage_baby_immunizations, name='immunization_manage_baby'),
    path('immunization/baby/<int:baby_id>/pdf/', baby_immunization_pdf, name='immunization_baby_pdf'),
    path('baby-profile/', baby_profile_view, name='baby_profile'),
    # Services: Centers & Clinics
    path('centers/', centers_list, name='centers_list'),
    path('centers/<slug:slug>/', center_detail, name='center_detail'),
    # Disease & Treatment informational pages
    path('care/antenatal/', antenatal_care, name='antenatal_care'),
    path('care/postnatal/', postnatal_care, name='postnatal_care'),
    path('care/immunization/', newborn_immunization, name='newborn_immunization'),
    # Discover
    path('find-doctor/', find_doctor, name='find_doctor'),
    path('articles/', articles, name='articles'),
    # Admin Dashboard
    path('admin-dashboard/', admin_dashboard_index, name='admin_dashboard'),
    path('admin-dashboard/export/appointments/', export_appointments_csv, name='admin_dashboard_export_appointments'),
    path('admin-dashboard/export/immunizations/', export_immunizations_csv, name='admin_dashboard_export_immunizations'),
    # Billing
    path('billing/', include('billing.urls')),
    # Case Files
    path('casefiles/', include('casefiles.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

