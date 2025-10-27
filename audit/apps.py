from django.apps import AppConfig, apps


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'

    def ready(self):
        # Import signal handlers and register targets dynamically
        from . import signals  # noqa: F401