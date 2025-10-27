from django.core.management.base import BaseCommand
from django.test import Client
from django.conf import settings

from accounts.models import User


class Command(BaseCommand):
    help = "Smoke test key routes and admin pages; reports any non-2xx/3xx responses."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=200, help='Max URLs to test')

    def handle(self, *args, **options):
        # Allow Django test client host
        if hasattr(settings, 'ALLOWED_HOSTS') and 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
        client = Client()
        # Ensure a superuser exists and log in
        admin_email = 'qa_admin@example.com'
        admin_password = 'qa123456'
        user = User.objects.filter(email=admin_email).first()
        if not user:
            user = User.objects.create_superuser(email=admin_email, password=admin_password)
        client.force_login(user)

        urls = [
            '/',
            '/dashboard/',
            '/dashboard/doctor/',
            '/dashboard/nurse/',
            '/dashboard/receptionist/',
            '/dashboard/pharmacist/',
            '/dashboard/lab-tech/',
            '/profile/',
            '/appointments/',
            '/appointments/new/',
            '/immunization/schedule/',
            '/immunization/schedule/all/',
            '/centers/',
            '/care/antenatal/',
            '/care/postnatal/',
            '/care/immunization/',
            '/find-doctor/',
            '/articles/',
            # Admin index and key models
            '/admin/',
            '/admin/accounts/user/',
            '/admin/audit/activitylog/',
            '/admin/patients/motherprofile/',
            '/admin/patients/babyprofile/',
            '/admin/immunization/immunizationschedule/',
            '/admin/immunization/vaccinationeventlog/',
            '/admin/casefiles/patientcasefile/',
            '/admin/appointments/appointment/',
        ]

        failures = []
        for url in urls:
            try:
                resp = client.get(url)
                code = resp.status_code
                if code >= 400:
                    failures.append((url, code))
                    self.stdout.write(self.style.ERROR(f"FAIL {code}: {url}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"OK {code}: {url}"))
            except Exception as e:
                failures.append((url, str(e)))
                self.stdout.write(self.style.ERROR(f"ERR {url}: {e}"))

        if failures:
            self.stdout.write(self.style.WARNING(f"Total failures: {len(failures)}"))
        else:
            self.stdout.write(self.style.SUCCESS("All tested URLs responded with < 400 status."))