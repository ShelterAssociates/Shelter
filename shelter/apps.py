from django.contrib.staticfiles.apps import StaticFilesConfig as BaseStaticFilesConfig


class StaticFilesConfig(BaseStaticFilesConfig):
    """collectstatic leaves out Django REST framework's files (old jQuery/Bootstrap of the
    browsable API, which the servers do not serve)."""

    ignore_patterns = BaseStaticFilesConfig.ignore_patterns + ["rest_framework/*"]
