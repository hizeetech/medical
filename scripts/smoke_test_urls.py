import sys
import os
import django
from django.conf import settings
from django.test import Client

"""
Run with: python manage.py shell -c "exec(open('scripts/smoke_test_urls.py').read())"
This performs a best-effort GET/POST across important URLs and prints failures.
"""

def main():
    client = Client()
    # Ensure test user exists
    from accounts.models import User
    admin_email = 'qa_admin@example.com'
    admin_password = 'qa123456'
    user = User.objects.filter(email=admin_email).first()
    if not user:
        user = User.objects.create_superuser(email=admin_email, password=admin_password)
    # Login
    assert client.login(email=admin_email, password=admin_password), 'Login failed'

    targets = [
        '/',
        '/dashboard/',
        '/dashboard/doctor/',
        '/dashboard/nurse/',
        '/dashboard/receptionist/',
        '/dashboard/pharmacist/',
        '/dashboard/lab-tech/',
        '/profile/',
        '/appointments/',
        '/immunization/schedule/',
        '/immunization/schedule/all/',
        '/centers/',
        '/care/antenatal/',
        '/care/postnatal/',
        '/care/immunization/',
        '/find-doctor/',
        '/articles/',
        '/admin/',
    ]

    failures = []
    for url in targets:
        resp = client.get(url)
        status = resp.status_code
        if status >= 400:
            failures.append((url, status))

    print('Smoke Test Results:')
    if not failures:
        print('OK: all targets returned < 400')
    else:
        for url, status in failures:
            print(f'FAIL {status}: {url}')
        print(f'Total failures: {len(failures)}')

if __name__ == '__main__':
    main()