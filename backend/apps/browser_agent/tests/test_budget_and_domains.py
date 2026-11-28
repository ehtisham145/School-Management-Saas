from decimal import Decimal

import pytest
from django.core.cache import cache

from apps.browser_agent import budget, services
from apps.browser_agent.domain_policy import check_domain, check_navigation
from apps.browser_agent.models import BrowserTask
from apps.browser_agent.url_policy import BlockedUrl


def blocked(url, check=check_domain):
    with pytest.raises(BlockedUrl) as error:
        check(url)
    return error.value.code


@pytest.mark.parametrize(
    "url",
    [
        "https://paypal.com/",
        "https://www.paypal.com/checkout",
        "https://WWW.PAYPAL.COM/",
        "https://paypal.com./",
        "http://a.b.paypal.com:8443/x",
        "https://www.absher.sa/",
    ],
)
def test_blocked_domains_cover_subdomains_case_and_trailing_dots(url):
    assert blocked(url) == "blocked_domain"


@pytest.mark.parametrize("url", ["https://notpaypal.com/", "https://paypal.com.evil.example/"])
def test_only_whole_labels_match(url):
    check_domain(url)


def test_the_allow_list_when_set(settings):
    settings.BROWSER_AGENT_ALLOWED_DOMAINS = ["Example.com"]
    check_domain("https://example.com/")
    check_domain("https://docs.example.com/")
    assert blocked("https://example.org/") == "domain_not_allowed"
    # Blocked wins over allowed.
    settings.BROWSER_AGENT_ALLOWED_DOMAINS = ["paypal.com"]
    assert blocked("https://paypal.com/") == "blocked_domain"


def test_navigation_checks_domains_before_addresses():
    assert blocked("https://paypal.com/", check_navigation) == "blocked_domain"
    assert blocked("http://169.254.169.254/", check_navigation) == "private_address"
    assert blocked("file:///etc/passwd", check_navigation) == "scheme"
    assert check_navigation("https://example.com/") == "example.com"


@pytest.mark.django_db
def test_month_spend_is_rebuilt_from_the_database_then_counted_in_the_cache(sara, omar):
    task = services.create_task(omar.school, user=omar.user, goal="Earlier")
    BrowserTask.objects.filter(pk=task.pk).update(cost_usd=Decimal("0.250000"))

    assert budget.month_spend() == Decimal("0.25")

    budget.add_spend(Decimal("0.000021"))
    assert budget.month_spend() == Decimal("0.250021")

    cache.clear()
    # Rebuilt from the database, which holds only what tasks recorded.
    assert budget.month_spend() == Decimal("0.25")


@pytest.mark.django_db
def test_recording_a_step_adds_its_cost_to_the_month(sara):
    task = services.create_task(sara.school, user=sara.user, goal="Find")
    task.model = "gpt-4o-mini"
    services.record_step(
        task,
        number=1,
        action="goto",
        domain="example.com",
        verdict="ok",
        input_tokens=1_000_000,
        output_tokens=0,
        model="gpt-4o-mini",
    )

    assert budget.month_spend() == Decimal("0.15")


@pytest.mark.django_db
def test_the_kill_switch(sara, settings):
    settings.BROWSER_AGENT_MONTHLY_BUDGET_USD = Decimal("0.10")
    assert not budget.is_exhausted()

    budget.add_spend(Decimal("0.10"))

    assert budget.is_exhausted()
