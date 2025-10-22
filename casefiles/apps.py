from django.apps import AppConfig


class CasefilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'casefiles'
    verbose_name = 'Patient Case Files'

    def ready(self):
        # Import signals to ensure handlers are registered
        from . import signals  # noqa: F401