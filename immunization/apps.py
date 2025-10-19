from django.apps import AppConfig


class ImmunizationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'immunization'

    def ready(self):
        from . import signals  # noqa: F401
