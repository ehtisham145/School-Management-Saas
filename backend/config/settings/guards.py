"""Start-up checks for settings. Pure functions, so tests can call them with plain dicts.

prod.py calls check_production(globals()) at import time, because gunicorn/uvicorn and
Celery never run Django's system checks. Locally, apps/browser_agent/checks.py runs the
browser agent part as a system check instead."""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ImproperlyConfigured


def env_decimal(env, name, *, default):
    """A money setting from the environment as Decimal; a bad value stops start-up."""
    raw = env.str(name, default=default)
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise ImproperlyConfigured(f"{name} must be a number, got {raw!r}.") from error
    if not value.is_finite() or value < 0:
        raise ImproperlyConfigured(f"{name} must be zero or more, got {raw!r}.")
    return value


def browser_agent_problems(settings):
    """Problems that must stop the browser agent from starting. `settings` is a mapping."""
    problems = []
    model = settings.get("BROWSER_AGENT_MODEL", "")
    prices = settings.get("BROWSER_AGENT_PRICES", {})
    if model not in prices:
        problems.append(
            f"BROWSER_AGENT_MODEL {model!r} has no price in BROWSER_AGENT_PRICES, "
            "so cost tracking and the budget would not work."
        )
    else:
        try:
            [Decimal(price) for price in prices[model]]
        except (InvalidOperation, TypeError, ValueError):
            problems.append(f"BROWSER_AGENT_PRICES[{model!r}] must be two numbers as text.")

    if settings.get("BROWSER_AGENT_ENABLED"):
        if not settings.get("OPENAI_API_KEY"):
            problems.append("BROWSER_AGENT_ENABLED is True but OPENAI_API_KEY is empty.")
    return problems


def production_problems(settings):
    problems = browser_agent_problems(settings)
    if settings.get("BROWSER_AGENT_ENABLED") and settings.get("CELERY_TASK_ALWAYS_EAGER"):
        problems.append(
            "BROWSER_AGENT_ENABLED is True but CELERY_TASK_ALWAYS_EAGER is on, so browser "
            "tasks would run inside web requests."
        )
    return problems


def check_production(settings):
    problems = production_problems(settings)
    if problems:
        raise ImproperlyConfigured(" ".join(problems))
