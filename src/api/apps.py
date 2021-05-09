from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'
    verbose_name = "Elinor API"

    def ready(self):
        import api.signals
