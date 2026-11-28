"""The platform's monthly browser agent spend and the kill switch.

The month's total is kept in the cache as whole micro-dollars (1 USD = 1,000,000), so each
step adds to it with one atomic `incr` instead of a SUM query. When the cache is empty
(restart, eviction, new month) it is rebuilt once from the tasks in the database.
Redis on servers makes it shared by every worker; locally the cache is per process."""

from decimal import ROUND_CEILING, Decimal

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.browser_agent import selectors

MICRO = Decimal(1_000_000)
KEY_TIMEOUT = 60 * 60 * 24 * 40  # longer than any month


def _month_start():
    today = timezone.localdate()
    return today.replace(day=1)


def _key(month_start):
    return f"browser_agent:spend:{month_start:%Y-%m}"


def _to_micro(amount):
    # Rounded up, so the counter never shows less than was spent.
    return int((Decimal(amount) * MICRO).to_integral_value(rounding=ROUND_CEILING))


def month_spend() -> Decimal:
    """USD spent this month (Riyadh time) by every workspace together."""
    month_start = _month_start()
    key = _key(month_start)
    micro = cache.get(key)
    if micro is None:
        micro = _to_micro(selectors.platform_spend_since(month_start))
        # add() keeps a value another worker wrote in the meantime.
        if not cache.add(key, micro, KEY_TIMEOUT):
            micro = cache.get(key, micro)
    return Decimal(micro) / MICRO


def add_spend(amount):
    amount = Decimal(amount)
    if amount <= 0:
        return
    key = _key(_month_start())
    try:
        cache.incr(key, _to_micro(amount))
    except ValueError:
        # Not in the cache: rebuild from the database, which already holds this step.
        cache.delete(key)
        month_spend()


def is_exhausted() -> bool:
    return month_spend() >= settings.BROWSER_AGENT_MONTHLY_BUDGET_USD
