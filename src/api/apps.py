from django.apps import AppConfig
from django.db.models.signals import post_migrate
from api.utils import update_assessment_version


class ApiConfig(AppConfig):
    name = "api"
    verbose_name = "Elinor API"

    def ready(self):
        import api.signals

        post_migrate.connect(
            update_assessment_version, dispatch_uid="update_assessment_version_migrate"
        )
