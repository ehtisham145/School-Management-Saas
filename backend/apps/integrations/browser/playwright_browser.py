"""Chromium through Playwright for the browser agent (ADR-0028).

One fresh context per task: no cookies or storage carried over, downloads off, service
workers blocked, images/media/fonts and known trackers dropped. Every request is checked
with the caller's URL check before it leaves. The context, browser and Playwright are
closed on exit even when something failed.

Locally this is the only network guard. On servers Chromium runs in its own sandbox
container whose only route out is the egress proxy (docs/browser-agent.md §2)."""

import logging
from contextlib import contextmanager, suppress
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

BLOCKED_RESOURCE_TYPES = frozenset({"image", "media", "font"})
TRACKER_DOMAINS = (
    "doubleclick.net",
    "google-analytics.com",
    "googletagmanager.com",
    "googlesyndication.com",
    "adservice.google.com",
    "facebook.net",
    "hotjar.com",
    "scorecardresearch.com",
    "clarity.ms",
)
ACTION_TIMEOUT_MS = 10_000
NAVIGATION_TIMEOUT_MS = 30_000
SETTLE_TIMEOUT_MS = 5_000
SCROLL_PIXELS = 700


class BrowserError(RuntimeError):
    """The browser couldn't start or stopped working. `code` is safe to log."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class BrowserActionError(RuntimeError):
    """One action failed on the page (element gone, timeout). The task can go on."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _is_tracker(host):
    return any(host == domain or host.endswith("." + domain) for domain in TRACKER_DOMAINS)


class PlaywrightBrowser:
    """Use as a context manager. `check_url(url)` must raise an exception to refuse a URL."""

    def __init__(self, *, check_url, headless=True):
        self._check_url = check_url
        self._headless = headless
        self._verdicts = {}
        self._playwright = self._browser = self._context = None
        self.page = None
        self.pages_visited = 0
        self.blocked_requests = 0

    # ------------------------------------------------------------ lifecycle
    def __enter__(self):
        try:
            from playwright.sync_api import Error, TimeoutError, sync_playwright
        except ImportError as error:
            raise BrowserError("playwright_not_installed") from error
        self._error_types = (Error, TimeoutError)
        self._timeout_type = TimeoutError
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._context = self._browser.new_context(
                accept_downloads=False, service_workers="block"
            )
            self._context.route("**/*", self._route)
            self.page = self._context.new_page()
            self.page.set_default_timeout(ACTION_TIMEOUT_MS)
            self.page.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
            self.page.on("framenavigated", self._on_navigated)
            # One tab only: a link that opens a new tab is closed at once.
            self._context.on("page", self._on_new_page)
        except Exception as error:
            self._close()
            raise BrowserError("launch_failed") from error
        return self

    def __exit__(self, *exc_info):
        self._close()
        return False

    def _close(self):
        for name, closer in (
            ("context", lambda: self._context and self._context.close()),
            ("browser", lambda: self._browser and self._browser.close()),
            ("playwright", lambda: self._playwright and self._playwright.stop()),
        ):
            try:
                closer()
            except Exception:
                logger.warning("browser_close_failed", extra={"part": name})
        self._playwright = self._browser = self._context = self.page = None

    # ------------------------------------------------------------ guards
    def _allowed(self, url):
        try:
            parts = urlsplit(url)
            # The port is part of the key: allowing example.com:443 must not allow :6379.
            key = (parts.scheme.lower(), (parts.hostname or "").lower(), parts.port)
        except ValueError:
            return False
        if key not in self._verdicts:
            try:
                self._check_url(url)
            except Exception:
                self._verdicts[key] = False
            else:
                self._verdicts[key] = True
        return self._verdicts[key]

    def _route(self, route):
        try:
            request = route.request
            host = (urlsplit(request.url).hostname or "").lower()
            if request.resource_type in BLOCKED_RESOURCE_TYPES or _is_tracker(host):
                route.abort()
            elif not self._allowed(request.url):
                self.blocked_requests += 1
                route.abort("blockedbyclient")
            else:
                route.continue_()
        except Exception:
            logger.warning("browser_route_failed")

    def _on_navigated(self, frame):
        if self.page is not None and frame == self.page.main_frame:
            if frame.url.startswith(("http://", "https://")):
                self.pages_visited += 1

    def _on_new_page(self, page):
        if page is not self.page:
            try:
                page.close()
            except Exception:
                logger.warning("browser_popup_close_failed")

    @contextmanager
    def _action(self):
        try:
            yield
        except self._timeout_type as error:
            raise BrowserActionError("timeout") from error
        except self._error_types as error:
            if self.page is None or self.page.is_closed():
                raise BrowserError("browser_closed") from error
            raise BrowserActionError("page_error") from error

    def _locate(self, ref):
        locator = self.page.locator(f'[data-agent-ref="{ref}"]')
        if locator.count() == 0:
            raise BrowserActionError("element_not_found")
        return locator.first

    def _settle(self):
        # A click that doesn't load a page is normal; just stop waiting.
        with suppress(*self._error_types):
            self.page.wait_for_load_state("domcontentloaded", timeout=SETTLE_TIMEOUT_MS)

    # ------------------------------------------------------------ actions
    @property
    def current_url(self):
        return self.page.url if self.page is not None else ""

    def run_script(self, script, arg):
        with self._action():
            return self.page.evaluate(script, arg)

    def goto(self, url):
        with self._action():
            self.page.goto(url, wait_until="domcontentloaded")

    def blank(self):
        with self._action():
            self.page.goto("about:blank")

    def click(self, ref):
        with self._action():
            element = self._locate(ref)
            element.evaluate("el => el.removeAttribute('target')")
            element.click()
            self._settle()

    def type(self, ref, text):
        with self._action():
            self._locate(ref).fill(text)

    def select(self, ref, option):
        with self._action():
            element = self._locate(ref)
            try:
                element.select_option(label=option)
            except self._error_types:
                element.select_option(value=option)

    def scroll(self, direction):
        with self._action():
            self.page.mouse.wheel(0, SCROLL_PIXELS if direction == "down" else -SCROLL_PIXELS)
            self.page.wait_for_timeout(300)

    def back(self):
        with self._action():
            self.page.go_back(wait_until="domcontentloaded")

    def wait(self):
        with self._action():
            self.page.wait_for_timeout(1500)
