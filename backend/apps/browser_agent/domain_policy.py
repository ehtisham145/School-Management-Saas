"""Blocked and allowed domains (BROWSER_AGENT_BLOCKED_DOMAINS / _ALLOWED_DOMAINS).

A rule covers the domain and every subdomain: "paypal.com" blocks "www.PayPal.com." too.
Matching is on whole labels, so "notpaypal.com" is not blocked by "paypal.com"."""

from django.conf import settings

from apps.browser_agent.url_policy import BlockedUrl, check_url, domain_of


def _normalise(domain):
    return (domain or "").strip().rstrip(".").lower()


def _matches(host, rules):
    for rule in rules:
        rule = _normalise(rule)
        if rule and (host == rule or host.endswith("." + rule)):
            return True
    return False


def check_domain(url):
    """Raise BlockedUrl when the URL's domain is blocked or not on a non-empty allow list."""
    host = _normalise(domain_of(url))
    if not host:
        return
    if _matches(host, settings.BROWSER_AGENT_BLOCKED_DOMAINS):
        raise BlockedUrl("blocked_domain")
    allowed = settings.BROWSER_AGENT_ALLOWED_DOMAINS
    if allowed and not _matches(host, allowed):
        raise BlockedUrl("domain_not_allowed")


def check_navigation(url):
    """Every navigation, redirect and request: domain rules first (no DNS), then the
    public-address check."""
    if isinstance(url, str) and url.lower().startswith(("http://", "https://")):
        check_domain(url)
    return check_url(url)
