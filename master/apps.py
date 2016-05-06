from django.apps import AppConfig

class MasterAppConfig(AppConfig):
    name = 'master'

    def ready(self):
        import signals