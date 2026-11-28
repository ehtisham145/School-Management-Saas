from decimal import Decimal

import pytest

from apps.browser_agent import url_policy
from apps.browser_agent.tests.fakes import fake_resolve
from apps.browser_agent.tests.teachers import Teacher
from apps.tenancy.models import School


@pytest.fixture
def sara(db):
    return Teacher("Sara")


@pytest.fixture
def omar(db):
    return Teacher("Omar")


@pytest.fixture
def lapsed(db):
    """A teacher whose plan has ended: the workspace is read-only."""
    return Teacher("Lina", subscribed=False)


@pytest.fixture
def school_teacher(db):
    """A teacher of a real school, not an individual workspace."""
    return Teacher("Hadi", kind=School.Kind.SCHOOL)


@pytest.fixture(autouse=True)
def no_real_dns(monkeypatch):
    """URL checks resolve names with a fake resolver, so tests never touch the network."""
    monkeypatch.setattr(url_policy, "_resolve", fake_resolve)


@pytest.fixture(autouse=True)
def agent_settings(settings):
    """Fixed values, so a developer's .env can't change what the tests expect."""
    settings.BROWSER_AGENT_ENABLED = True
    settings.BROWSER_AGENT_MODEL = "gpt-4o-mini"
    settings.BROWSER_AGENT_MONTHLY_BUDGET_USD = Decimal("100")
    settings.BROWSER_AGENT_MAX_COST_USD_PER_TASK = Decimal("0.20")
    settings.BROWSER_AGENT_MAX_RUNNING_PER_USER = 1
    settings.BROWSER_AGENT_MAX_RUNNING_TOTAL = 10
    settings.BROWSER_AGENT_BLOCKED_DOMAINS = ["paypal.com", "absher.sa"]
    settings.BROWSER_AGENT_ALLOWED_DOMAINS = []
    settings.BROWSER_AGENT_ALLOWED_PORTS = [80, 443]
    settings.BROWSER_AGENT_DNS_TIMEOUT_SECONDS = 3.0


@pytest.fixture(autouse=True)
def fresh_dns_pool():
    """Each test starts with an empty DNS pool, so a test that fills it can't leak."""
    url_policy.reset_dns_pool()
    yield
    url_policy.reset_dns_pool()
