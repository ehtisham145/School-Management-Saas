from django.apps import AppConfig


class BrowserAgentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.browser_agent"

    def ready(self):
        from apps.browser_agent import checks  # noqa: F401 - registers the system check
