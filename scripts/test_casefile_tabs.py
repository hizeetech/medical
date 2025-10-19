import os
import sys
import django

# Ensure project base dir is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_main.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from accounts.models import User
from patients.models import MotherProfile
from casefiles.models import PatientCaseFile


def get_or_create_user(email, role):
    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create_user(email=email, password='pass1234', role=role)
    return user


def get_or_create_mother(user):
    mother = MotherProfile.objects.filter(user=user).first()
    if not mother:
        mother = MotherProfile.objects.create(user=user, full_name='Test Mother')
    return mother


def get_or_create_casefile(mother, created_by):
    case_file = PatientCaseFile.objects.filter(patient=mother).first()
    if not case_file:
        case_file = PatientCaseFile.objects.create(patient=mother, created_by=created_by)
    return case_file


def main():
    doctor = get_or_create_user('doctor@test.local', 'DOCTOR')
    patient_user = get_or_create_user('patient@test.local', 'PATIENT')
    mother = get_or_create_mother(patient_user)
    case_file = get_or_create_casefile(mother, doctor)

    client = Client()
    client.force_login(doctor)

    urls = [
        reverse('casefile_tab_patient_info', args=[case_file.id]),
        reverse('casefile_tab_medical_history', args=[case_file.id]),
        reverse('casefile_tab_visits', args=[case_file.id]),
        reverse('casefile_tab_prescriptions', args=[case_file.id]),
        reverse('casefile_tab_lab_results', args=[case_file.id]),
        reverse('casefile_tab_billing', args=[case_file.id]),
        reverse('casefile_tab_maternity', args=[case_file.id]),
        reverse('casefile_tab_attachments', args=[case_file.id]),
        reverse('casefile_tab_access', args=[case_file.id]),
    ]

    for u in urls:
        resp = client.get(u)
        status = resp.status_code
        print(f"GET {u} -> {status}")
        if status != 200:
            print("--- Response content (truncated) ---")
            try:
                content = resp.content.decode('utf-8', errors='replace')
            except Exception:
                content = str(resp.content)
            print(content[:2000])
            print("--- END ---")


if __name__ == '__main__':
    main()