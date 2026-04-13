from django.apps import AppConfig


class AnalyzerConfig(AppConfig):
    """Django app config: registers the analyzer app name."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analyzer"
