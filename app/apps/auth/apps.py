from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auth'
    label = 'custom_auth'
    verbose_name = 'Authentication & Permissions'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        """
        try:
            import apps.auth.signals
        except ImportError:
            pass