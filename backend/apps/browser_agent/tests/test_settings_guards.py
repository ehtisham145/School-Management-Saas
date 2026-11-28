from decimal import Decimal

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.browser_agent.checks import browser_agent_settings
from config.settings.guards import (
    browser_agent_problems,
    check_production,
    env_decimal,
    production_problems,
)

GOOD = {
    "BROWSER_AGENT_ENABLED": True,
    "OPENAI_API_KEY": "sk-test",
    "BROWSER_AGENT_MODEL": "gpt-4o-mini",
    "BROWSER_AGENT_PRICES": {"gpt-4o-mini": ("0.15", "0.60")},
    "CELERY_TASK_ALWAYS_EAGER": False,
}


def settings_with(**changes):
    return {**GOOD, **changes}


def test_good_production_settings_pass():
    check_production(GOOD)
    check_production(settings_with(BROWSER_AGENT_ENABLED=False, OPENAI_API_KEY=""))


def test_enabled_without_an_openai_key_stops_start_up():
    with pytest.raises(ImproperlyConfigured, match="OPENAI_API_KEY"):
        check_production(settings_with(OPENAI_API_KEY=""))


def test_enabled_with_eager_celery_stops_start_up():
    with pytest.raises(ImproperlyConfigured, match="CELERY_TASK_ALWAYS_EAGER"):
        check_production(settings_with(CELERY_TASK_ALWAYS_EAGER=True))


def test_eager_celery_is_fine_while_the_agent_is_off():
    assert (
        production_problems(
            settings_with(BROWSER_AGENT_ENABLED=False, CELERY_TASK_ALWAYS_EAGER=True)
        )
        == []
    )


def test_a_model_without_a_price_stops_start_up_even_when_off():
    with pytest.raises(ImproperlyConfigured, match="has no price"):
        check_production(settings_with(BROWSER_AGENT_ENABLED=False, BROWSER_AGENT_MODEL="gpt-9"))


def test_a_price_that_is_not_a_number_stops_start_up():
    problems = browser_agent_problems(
        settings_with(BROWSER_AGENT_PRICES={"gpt-4o-mini": ("cheap", "0.60")})
    )
    assert problems and "two numbers" in problems[0]


def test_every_problem_is_reported_at_once():
    problems = production_problems(
        settings_with(OPENAI_API_KEY="", CELERY_TASK_ALWAYS_EAGER=True, BROWSER_AGENT_MODEL="x")
    )
    assert len(problems) == 3


def test_money_settings_are_decimal_and_bad_values_stop_start_up(monkeypatch):
    env = environ.Env()
    monkeypatch.setenv("TEST_MONEY", "0.20")
    assert env_decimal(env, "TEST_MONEY", default="1") == Decimal("0.20")
    assert env_decimal(env, "TEST_MONEY_MISSING", default="100") == Decimal("100")

    for bad in ("abc", "-1", "NaN", "Infinity"):
        monkeypatch.setenv("TEST_MONEY", bad)
        with pytest.raises(ImproperlyConfigured, match="TEST_MONEY"):
            env_decimal(env, "TEST_MONEY", default="1")


def test_the_system_check_reports_the_same_problems(settings):
    settings.BROWSER_AGENT_ENABLED = True
    settings.OPENAI_API_KEY = ""
    settings.BROWSER_AGENT_MODEL = "gpt-9"

    errors = browser_agent_settings(None)

    assert {error.id for error in errors} == {"browser_agent.E001", "browser_agent.E002"}


def test_the_system_check_passes_with_good_settings(settings):
    settings.BROWSER_AGENT_ENABLED = False
    settings.BROWSER_AGENT_MODEL = "gpt-4o-mini"
    assert browser_agent_settings(None) == []


def test_the_shipped_defaults_are_consistent(settings):
    assert settings.BROWSER_AGENT_SOFT_TIME_LIMIT == settings.BROWSER_AGENT_MAX_SECONDS
    assert settings.BROWSER_AGENT_HARD_TIME_LIMIT == settings.BROWSER_AGENT_MAX_SECONDS + 30
    assert settings.CELERY_TASK_ROUTES["apps.browser_agent.tasks.run_browser_task_job"] == {
        "queue": "browser"
    }
    assert "browser_agent" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
