"""Which URLs the agent's browser may open.

Only public http(s) addresses on allowed ports (BROWSER_AGENT_ALLOWED_PORTS, default 80
and 443). Loopback, private ranges, link-local (cloud metadata at 169.254.169.254),
carrier-grade NAT, documentation and reserved ranges, internal names and every other
scheme are refused, after resolving the name, so a public-looking name that points inside
is refused too.

- Hosts are read the way Chromium reads them: "127.1", "0x7f.0.0.1", "017700000001" and
  "2130706433" are all 127.0.0.1, and are checked as addresses before any DNS lookup.
- Blocked ranges are listed here, on top of Python's `is_global`, so the result doesn't
  depend on the Python patch release. NAT64 (64:ff9b::/96) is checked by the IPv4 inside
  it; 6to4 (2002::/16) and Teredo (2001::/32) are refused outright.
- DNS lookups run in a small bounded thread pool with a timeout
  (BROWSER_AGENT_DNS_TIMEOUT_SECONDS). A slow lookup refuses the URL ("unresolvable"), and
  when every slot is taken by slow lookups the URL is refused at once ("dns_busy").
  Nothing waits forever and the thread count never grows past the pool size.

This check runs in the controller. On servers the browser's only route out is the egress
proxy, which repeats it at connect time and closes the DNS-rebinding gap
(docs/browser-agent.md §6, T2)."""

import ipaddress
import os
import re
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

from django.conf import settings

ALLOWED_SCHEMES = frozenset({"http", "https"})
INTERNAL_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".corp", ".intranet")
DNS_POOL_SIZE = 8

_BLOCKED_V4 = tuple(
    ipaddress.ip_network(network)
    for network in (
        "0.0.0.0/8",  # "this network"
        "10.0.0.0/8",
        "100.64.0.0/10",  # carrier-grade NAT
        "127.0.0.0/8",
        "169.254.0.0/16",  # link-local, cloud metadata
        "172.16.0.0/12",
        "192.0.0.0/24",  # IETF protocol assignments
        "192.0.2.0/24",  # documentation
        "192.88.99.0/24",  # 6to4 relay anycast
        "192.168.0.0/16",
        "198.18.0.0/15",  # benchmarking
        "198.51.100.0/24",  # documentation
        "203.0.113.0/24",  # documentation
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved, includes 255.255.255.255
    )
)
_BLOCKED_V6 = tuple(
    ipaddress.ip_network(network)
    for network in (
        "::/96",  # unspecified, loopback, IPv4-compatible
        "::ffff:0:0:0/96",  # IPv4-translated
        "64:ff9b:1::/48",  # local-use NAT64
        "100::/64",  # discard
        "2001::/23",  # IETF protocol assignments, includes Teredo 2001::/32
        "2001:db8::/32",  # documentation
        "2002::/16",  # 6to4
        "fc00::/7",  # unique local
        "fe80::/10",  # link-local
        "fec0::/10",  # old site-local
        "ff00::/8",  # multicast
    )
)
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_HEX = re.compile(r"[0-9a-f]*")
_OCTAL = re.compile(r"[0-7]+")
_DECIMAL = re.compile(r"[0-9]+")


class BlockedUrl(Exception):
    """The URL may not be opened. `code` is a short reason that is safe to log."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------- addresses


def is_public_ip(address) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif ip in _NAT64:
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    blocked = _BLOCKED_V4 if isinstance(ip, ipaddress.IPv4Address) else _BLOCKED_V6
    if any(ip in network for network in blocked):
        return False
    return ip.is_global and not ip.is_multicast


def _ipv4_number(part):
    """One dotted part as Chromium reads it (decimal, 0x hex, 0-led octal), or None."""
    if part[:2].lower() == "0x":
        digits = part[2:]
        return int(digits or "0", 16) if _HEX.fullmatch(digits.lower()) else None
    if len(part) > 1 and part[0] == "0":
        return int(part[1:], 8) if _OCTAL.fullmatch(part[1:]) else None
    return int(part) if _DECIMAL.fullmatch(part) else None


def _legacy_ipv4(host):
    """The IPv4 address a numeric host stands for, None for a normal name, or BlockedUrl
    when it ends in a number but isn't a valid address (WHATWG URL rules)."""
    parts = host.split(".")
    if not parts or not parts[-1] or _ipv4_number(parts[-1]) is None:
        return None
    numbers = [_ipv4_number(part) if part else None for part in parts]
    if len(parts) > 4 or None in numbers or any(number > 255 for number in numbers[:-1]):
        raise BlockedUrl("invalid_url")
    if numbers[-1] >= 256 ** (5 - len(numbers)):
        raise BlockedUrl("invalid_url")
    value = numbers[-1] + sum(n * 256 ** (3 - i) for i, n in enumerate(numbers[:-1]))
    return str(ipaddress.IPv4Address(value))


def domain_of(url) -> str:
    """The host name only, lowercase, for logs. Never the path or query."""
    try:
        return (urlsplit(url).hostname or "").rstrip(".").lower()[:253]
    except ValueError:
        return ""


# ---------------------------------------------------------------- DNS


def _resolve(host):
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return {info[4][0] for info in infos}


_pool_lock = threading.Lock()
_pool = _slots = _pool_pid = None


def _dns_pool():
    """Made on first use and again in a forked child (Celery prefork), where the parent's
    threads don't exist."""
    global _pool, _slots, _pool_pid
    with _pool_lock:
        if _pool is None or _pool_pid != os.getpid():
            _pool = ThreadPoolExecutor(max_workers=DNS_POOL_SIZE, thread_name_prefix="dns")
            _slots = threading.BoundedSemaphore(DNS_POOL_SIZE)
            _pool_pid = os.getpid()
        return _pool, _slots


def reset_dns_pool():
    """For tests."""
    global _pool, _slots, _pool_pid
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown(wait=False, cancel_futures=True)
        _pool = _slots = _pool_pid = None


def _lookup(resolve, host, timeout):
    pool, slots = _dns_pool()
    # One slot per lookup still running, timed out or not. No free slot: refuse now,
    # so slow lookups can never queue up or add threads.
    if not slots.acquire(blocking=False):
        raise BlockedUrl("dns_busy")
    try:
        future = pool.submit(resolve, host)
    except RuntimeError as error:
        slots.release()
        raise BlockedUrl("dns_busy") from error
    future.add_done_callback(lambda _: slots.release())
    try:
        return future.result(timeout=timeout)
    except TimeoutError as error:
        # The lookup keeps its slot until the resolver gives up on its own.
        raise BlockedUrl("unresolvable") from error
    except Exception as error:
        # Any resolver failure (OSError, UnicodeError, ...) refuses the URL.
        raise BlockedUrl("unresolvable") from error


# ---------------------------------------------------------------- check


def check_url(url, *, resolve=None, timeout=None) -> str:
    """Return the host if the URL is allowed, or raise BlockedUrl.

    `resolve(host) -> set of addresses` and `timeout` (seconds) are for tests."""
    resolve = resolve or _resolve
    if timeout is None:
        timeout = settings.BROWSER_AGENT_DNS_TIMEOUT_SECONDS
    if not isinstance(url, str) or not url.strip() or len(url) > 2000:
        raise BlockedUrl("invalid_url")
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
        port = parts.port  # raises ValueError for a bad port
    except ValueError as error:
        raise BlockedUrl("invalid_url") from error

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise BlockedUrl("scheme")
    if parts.username or parts.password:
        raise BlockedUrl("credentials_in_url")
    if not host:
        raise BlockedUrl("no_host")
    host = host.rstrip(".").lower()

    if ":" in host:
        try:
            literal = str(ipaddress.IPv6Address(host.split("%", 1)[0]))
        except ValueError as error:
            raise BlockedUrl("invalid_url") from error
    else:
        literal = _legacy_ipv4(host)

    if literal is not None:
        if not is_public_ip(literal):
            raise BlockedUrl("private_address")
    elif host == "localhost" or host.endswith(INTERNAL_SUFFIXES) or "." not in host:
        raise BlockedUrl("internal_name")

    if port is not None and port not in settings.BROWSER_AGENT_ALLOWED_PORTS:
        raise BlockedUrl("port")
    if literal is not None:
        return literal

    addresses = _lookup(resolve, host, timeout)
    if not addresses:
        raise BlockedUrl("unresolvable")
    for address in addresses:
        try:
            public = is_public_ip(address)
        except ValueError:
            public = False
        if not public:
            raise BlockedUrl("private_address")
    return host
