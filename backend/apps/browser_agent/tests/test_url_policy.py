import socket
import threading
import time

import pytest

from apps.browser_agent import url_policy
from apps.browser_agent.url_policy import BlockedUrl, check_url, domain_of, is_public_ip
from apps.integrations.browser.playwright_browser import PlaywrightBrowser


def public(host):
    return {"93.184.216.34"}


def must_not_resolve(host):
    raise AssertionError("A literal IP or blocked name must be refused before DNS.")


def blocked_code(url, resolve=must_not_resolve, **kwargs):
    with pytest.raises(BlockedUrl) as error:
        check_url(url, resolve=resolve, **kwargs)
    return error.value.code


# ---------------------------------------------------------------- addresses


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.1.2.3:8000/admin",
        "http://127.1/",
        "http://0x7f.0.0.1/",
        "http://0x7F000001/",
        "http://017700000001/",
        "http://0177.0.0.1/",
        "http://2130706433/",
        "http://10.0.0.5/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://100.64.0.1/",
        "http://0.0.0.0/",
        "http://0/",
        "http://224.0.0.1/",
        "http://[::1]/",
        "http://[fd00::1]/",
        "http://[fe80::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[::ffff:169.254.169.254]/",
    ],
)
def test_private_and_special_addresses_are_refused(url):
    assert blocked_code(url) == "private_address"


@pytest.mark.parametrize(
    "address",
    [
        # Pinned here so a Python patch release can't change the answer.
        "100.64.0.1",
        "100.127.255.255",
        "0.0.0.0",  # noqa: S104 - checked as blocked, nothing binds to it
        "0.1.2.3",
        "192.0.0.1",
        "192.0.0.9",
        "192.0.0.10",
        "192.0.2.1",
        "192.88.99.1",
        "198.18.0.1",
        "198.19.255.255",
        "198.51.100.1",
        "203.0.113.1",
        "240.0.0.1",
        "255.255.255.255",
        "::",
        "::127.0.0.1",
        "::ffff:0:10.0.0.1",
        "64:ff9b::7f00:1",
        "64:ff9b::a9fe:a9fe",
        "64:ff9b:1::1",
        "2002:5db8:d822::1",
        "2002:7f00:1::1",
        "2001:0:4136:e378::1",
        "2001:db8::1",
        "100::1",
        "fec0::1",
        "ff02::1",
    ],
)
def test_special_ranges_are_never_public(address):
    assert not is_public_ip(address)


@pytest.mark.parametrize(
    "address",
    ["93.184.216.34", "8.8.8.8", "2606:2800:220:1:248:1893:25c8:1946", "64:ff9b::808:808"],
)
def test_public_addresses_are_public(address):
    # 64:ff9b::808:808 is NAT64 for 8.8.8.8: checked by the address inside.
    assert is_public_ip(address)


def test_a_name_resolving_to_nat64_of_a_private_address_is_refused():
    assert blocked_code("https://sneaky.example/", lambda host: {"64:ff9b::a00:1"}) == (
        "private_address"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://1.2.3.4.5/",
        "http://256.1.1.1/",
        "http://08.1.1.1/",
        "http://example.123/",
        "http://1..1/",
        "http://4294967296/",
    ],
)
def test_hosts_that_end_in_a_number_but_are_not_addresses_are_refused(url):
    assert blocked_code(url) == "invalid_url"


def test_a_public_numeric_host_is_returned_as_a_normal_address():
    assert check_url("http://0x5db8d822/", resolve=must_not_resolve) == "93.184.216.34"


# ---------------------------------------------------------------- schemes and names


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/",
        "javascript:alert(1)",
        "data:text/html,hello",
        "chrome://settings",
        "ws://example.com/",
    ],
)
def test_only_http_and_https_are_allowed(url):
    assert blocked_code(url) == "scheme"


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/",
        "http://app.localhost/",
        "http://db/",
        "http://redis:6379/",
        "http://api.internal/",
        "http://printer.local/",
    ],
)
def test_internal_names_are_refused(url):
    assert blocked_code(url) == "internal_name"


def test_a_public_name_that_resolves_inside_is_refused():
    assert blocked_code("https://inside.example/", lambda host: {"10.0.0.1"}) == "private_address"


def test_one_private_address_among_public_ones_is_enough_to_refuse():
    addresses = lambda host: {"93.184.216.34", "127.0.0.1"}  # noqa: E731
    assert blocked_code("https://mixed.example/", addresses) == "private_address"


def test_credentials_in_the_url_are_refused():
    assert blocked_code("http://user:pass@example.com/") == "credentials_in_url"


@pytest.mark.parametrize("url", ["", "   ", None, "https://example.com:99999/", "x" * 2001])
def test_malformed_urls_are_refused(url):
    assert blocked_code(url) == "invalid_url"


def test_a_very_long_url_is_refused():
    assert blocked_code("https://example.com/" + "a" * 2000) == "invalid_url"


def test_public_urls_are_allowed_and_return_the_lowercase_host():
    assert check_url("https://Example.COM./path?q=1", resolve=public) == "example.com"
    assert check_url("http://93.184.216.34/", resolve=must_not_resolve) == "93.184.216.34"
    assert (
        check_url("https://[2606:2800:220:1:248:1893:25c8:1946]/", resolve=must_not_resolve)
        == "2606:2800:220:1:248:1893:25c8:1946"
    )


def test_domain_of_keeps_only_the_host():
    assert domain_of("https://Sub.Example.com/a/b?token=secret#x") == "sub.example.com"
    assert domain_of("not a url") == ""
    assert domain_of("") == ""


# ---------------------------------------------------------------- ports


@pytest.mark.parametrize("port", [22, 3306, 6379, 0, 8080, 8443, 65535])
def test_only_allowed_ports_are_opened(port):
    assert blocked_code(f"https://example.com:{port}/", public) == "port"
    assert blocked_code(f"http://93.184.216.34:{port}/") == "port"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/",
        "http://example.com:80/",
        "https://example.com:443/",
        "https://example.com/",
        "https://example.com:80/",
    ],
)
def test_default_and_allowed_ports_are_opened(url):
    assert check_url(url, resolve=public) == "example.com"


def test_the_port_list_comes_from_settings(settings):
    settings.BROWSER_AGENT_ALLOWED_PORTS = [443, 8443]
    assert check_url("https://example.com:8443/", resolve=public) == "example.com"
    assert blocked_code("http://example.com:80/", public) == "port"


def test_the_browser_checks_each_port_on_its_own():
    seen = []

    def check(url):
        seen.append(url)
        if url.endswith(":6379/"):
            raise BlockedUrl("port")

    browser = PlaywrightBrowser(check_url=check)

    assert browser._allowed("https://example.com/")
    assert not browser._allowed("https://example.com:6379/")
    assert browser._allowed("https://example.com/again")  # cached for the same port
    assert not browser._allowed("https://example.com:99999/")
    assert seen == ["https://example.com/", "https://example.com:6379/"]


# ---------------------------------------------------------------- DNS


def test_a_slow_lookup_is_refused_within_the_timeout():
    def slow(host):
        time.sleep(2)
        return {"93.184.216.34"}

    started = time.monotonic()
    assert blocked_code("https://slow.example/", slow, timeout=0.2) == "unresolvable"
    assert time.monotonic() - started < 1


def test_the_timeout_comes_from_settings(settings):
    settings.BROWSER_AGENT_DNS_TIMEOUT_SECONDS = 0.1
    release = threading.Event()

    def stuck(host):
        release.wait(5)
        return {"93.184.216.34"}

    try:
        assert blocked_code("https://stuck.example/", stuck) == "unresolvable"
    finally:
        release.set()


def test_a_fast_lookup_still_works():
    assert check_url("https://fast.example/", resolve=public, timeout=0.5) == "fast.example"


def test_resolver_errors_are_refused():
    def fail(host):
        raise socket.gaierror("no such host")

    def odd(host):
        raise ValueError("bad answer")

    assert blocked_code("https://nowhere.example/", fail) == "unresolvable"
    assert blocked_code("https://odd.example/", odd) == "unresolvable"
    assert blocked_code("https://empty.example/", lambda host: set()) == "unresolvable"


def test_a_full_pool_fails_closed_at_once_and_recovers():
    release = threading.Event()

    def stuck(host):
        release.wait(10)
        return {"93.184.216.34"}

    try:
        # Each slow lookup times out but keeps its slot until the resolver returns.
        for index in range(url_policy.DNS_POOL_SIZE):
            assert blocked_code(f"https://slow{index}.example/", stuck, timeout=0.05) == (
                "unresolvable"
            )

        started = time.monotonic()
        assert blocked_code("https://next.example/", public, timeout=5) == "dns_busy"
        assert time.monotonic() - started < 0.5
        # This pool's threads only: an earlier test's slow lookup may still be finishing
        # in its own, already replaced pool.
        pool, _ = url_policy._dns_pool()
        assert len(pool._threads) <= url_policy.DNS_POOL_SIZE
    finally:
        release.set()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            assert check_url("https://after.example/", resolve=public, timeout=1)
            break
        except BlockedUrl:
            time.sleep(0.05)
    else:
        pytest.fail("The pool did not recover after the slow lookups finished.")
