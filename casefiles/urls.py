from django.urls import path
from . import views

urlpatterns = [
    path('', views.casefile_search, name='casefiles_search'),
    path('open/<int:patient_id>/', views.open_or_create_casefile, name='casefiles_open'),
    path('<int:casefile_id>/', views.casefile_detail, name='casefile_detail'),
    # Tab content endpoints (HTMX)
    path('<int:casefile_id>/tabs/patient-info/', views.tab_patient_info, name='casefile_tab_patient_info'),
    path('<int:casefile_id>/tabs/medical-history/', views.tab_medical_history, name='casefile_tab_medical_history'),
    path('<int:casefile_id>/tabs/visits/', views.tab_visits, name='casefile_tab_visits'),
    path('<int:casefile_id>/tabs/prescriptions/', views.tab_prescriptions, name='casefile_tab_prescriptions'),
    path('<int:casefile_id>/tabs/lab-results/', views.tab_lab_results, name='casefile_tab_lab_results'),
    path('<int:casefile_id>/tabs/billing/', views.tab_billing, name='casefile_tab_billing'),
    path('<int:casefile_id>/tabs/maternity/', views.tab_maternity, name='casefile_tab_maternity'),
    path('<int:casefile_id>/tabs/attachments/', views.tab_attachments, name='casefile_tab_attachments'),
    path('<int:casefile_id>/tabs/access/', views.tab_access, name='casefile_tab_access'),
    # Create actions
    path('<int:casefile_id>/medical-history/new/', views.medical_history_new, name='casefile_medical_history_new'),
    path('<int:casefile_id>/visits/new/', views.visit_new, name='casefile_visit_new'),
    path('<int:casefile_id>/prescriptions/new/', views.prescription_new, name='casefile_prescription_new'),
    path('<int:casefile_id>/lab-results/new/', views.lab_result_new, name='casefile_lab_result_new'),
    path('<int:casefile_id>/attachments/new/', views.attachment_new, name='casefile_attachment_new'),
    path('<int:casefile_id>/billing/new/', views.billing_new, name='casefile_billing_new'),
    path('<int:casefile_id>/maternity/baby/new/', views.baby_new, name='casefile_baby_new'),
    path('<int:casefile_id>/access/new/', views.access_log_new, name='casefile_access_new'),
    # Status updates
    path('prescriptions/<int:pk>/status/', views.prescription_status_update, name='casefile_prescription_status'),
]