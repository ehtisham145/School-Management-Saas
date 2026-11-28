"""System checks for the browser agent (runserver, migrate, `manage.py check`).

Production also runs the same rules at import time in prod.py, because gunicorn, uvicorn
and Celery never run system checks."""

from django.conf import settings
from django.core.checks import Error, register

from config.settings.guards import browser_agent_problems


@register()
def browser_agent_settings(app_configs, **kwargs):
    names = (
        "BROWSER_AGENT_MODEL",
        "BROWSER_AGENT_PRICES",
        "BROWSER_AGENT_ENABLED",
        "OPENAI_API_KEY",
    )
    values = {name: getattr(settings, name, None) for name in names}
    return [
        Error(problem, id=f"browser_agent.E00{index}")
        for index, problem in enumerate(browser_agent_problems(values), start=1)
    ]
