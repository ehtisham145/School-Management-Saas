"""The browser agent's loop (docs/browser-agent.md §4).

snapshot → mask → AI picks one action → URL check → act → record the step → repeat,
until the AI says done or a limit is hit. The AI only ever sees masked text; real values
are put back here, on our server, when typing. URLs are never unmasked, so personal data
can't be sent out in a link."""

import logging
import time
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings

from apps.browser_agent import actions as act
from apps.browser_agent import budget, selectors, services
from apps.browser_agent.domain_policy import check_navigation
from apps.browser_agent.masking import PLACEHOLDER, MaskVault
from apps.browser_agent.models import BrowserStep, BrowserTask
from apps.browser_agent.snapshot import EXTRACT_SCRIPT, format_snapshot, script_arg
from apps.browser_agent.url_policy import BlockedUrl, domain_of
from apps.integrations.ai import agent_provider
from apps.integrations.browser.playwright_browser import (
    BrowserActionError,
    BrowserError,
    PlaywrightBrowser,
)

logger = logging.getLogger(__name__)

HISTORY_LINES = 6
MAX_NOTES = 10
# An AI call is started only with this much time left: its worst case (every attempt
# times out) plus a buffer, so the task ends as "max_seconds" instead of Celery's limit.
TIME_RESERVE_SECONDS = agent_provider.WORST_CASE_CALL_SECONDS + 10
Status = BrowserTask.Status
Verdict = BrowserStep.Verdict


@dataclass(frozen=True)
class Limits:
    max_steps: int
    max_seconds: int
    max_input_tokens: int
    max_pages: int
    max_strikes: int
    max_page_chars: int
    max_cost_usd: Decimal

    @classmethod
    def from_settings(cls):
        return cls(
            max_steps=settings.BROWSER_AGENT_MAX_STEPS,
            max_seconds=settings.BROWSER_AGENT_MAX_SECONDS,
            max_input_tokens=settings.BROWSER_AGENT_MAX_INPUT_TOKENS,
            max_pages=settings.BROWSER_AGENT_MAX_PAGES,
            max_strikes=settings.BROWSER_AGENT_MAX_STRIKES,
            max_page_chars=settings.BROWSER_AGENT_MAX_PAGE_CHARS,
            max_cost_usd=settings.BROWSER_AGENT_MAX_COST_USD_PER_TASK,
        )


def playwright_opener(*, headless=True):
    # Every request the page makes, not only navigations, goes through the same check.
    return lambda: PlaywrightBrowser(check_url=check_navigation, headless=headless)


def run_task(
    task,
    *,
    open_browser=None,
    next_action=None,
    limits=None,
    clock=time.monotonic,
    on_step=None,
):
    """Run one task to the end and return it. Never raises for page or provider failures.

    A task that already ended is returned untouched: it never runs twice."""
    if task.status in BrowserTask.FINISHED:
        return task
    user = task.created_by
    vault = MaskVault(known=[user.get_full_name(), user.first_name, user.last_name, user.email])
    run = _Run(
        task=task,
        vault=vault,
        limits=limits or Limits.from_settings(),
        next_action=next_action or agent_provider.next_action,
        clock=clock,
        on_step=on_step,
        model=settings.BROWSER_AGENT_MODEL,
    )
    if not services.mark_running(task, model=run.model):
        return task
    try:
        # Leaving this block closes the context, browser and Playwright, also on errors
        # and on Celery's soft time limit.
        with (open_browser or playwright_opener())() as browser:
            status, reason, answer = run.drive(browser)
    except SoftTimeLimitExceeded:
        status, reason, answer = Status.FAILED, "time_limit", run.notes_answer()
    except agent_provider.AgentAiUnavailable as error:
        # Not configured, unpriced model or provider down. Tokens, if any, are recorded.
        status, reason, answer = Status.FAILED, error.code[:40], run.notes_answer()
    except BrowserError as error:
        status, reason, answer = Status.FAILED, f"browser_{error.code}", run.notes_answer()
    except Exception as error:
        # Only the type is logged: messages from the page layer can hold typed values.
        logger.error(
            "browser_agent_crashed", extra={"task_id": task.pk, "error": type(error).__name__}
        )
        status, reason, answer = Status.FAILED, "internal_error", run.notes_answer()
    return services.finish_task(task, status=status, answer=answer, failure_reason=reason)


class _Run:
    def __init__(self, *, task, vault, limits, next_action, clock, on_step, model):
        self.task = task
        self.vault = vault
        self.limits = limits
        self.next_action = next_action
        self.clock = clock
        self.on_step = on_step
        self.model = model
        self.history = []
        self.notes = []
        self.strikes = 0
        self.time_left = None

    def notes_answer(self):
        return self.vault.unmask("\n".join(self.notes))

    def drive(self, browser):
        started = self.clock()
        goal = self.vault.mask(self.task.goal)

        if self.task.start_url:
            try:
                check_navigation(self.task.start_url)
                browser.goto(self.task.start_url)
            except BlockedUrl as error:
                return Status.FAILED, f"start_url_{error.code}", ""
            except BrowserActionError:
                return Status.FAILED, "start_page_failed", ""

        limits = self.limits
        for number in range(1, limits.max_steps + 1):
            stop = self._limit_reached(browser, started)
            if stop is not None:
                return stop

            step_started = self.clock()
            page = self.vault.mask(self._page_text(browser))
            try:
                reply = self.next_action(
                    goal=goal,
                    history=self.history[-HISTORY_LINES:],
                    notes=self.notes,
                    page=page,
                    schema=act.ACTION_SCHEMA,
                    model=self.model,
                    time_left=self.time_left,
                )
            except agent_provider.AgentAiUnavailable as error:
                # Tokens the provider billed are charged even when its reply is unusable,
                # so the cost ceiling and the monthly budget can't be bypassed.
                if error.input_tokens or error.output_tokens:
                    self._record(
                        number,
                        "ai_error",
                        Verdict.INVALID,
                        error.code,
                        step_started,
                        browser,
                        input_tokens=error.input_tokens,
                        output_tokens=error.output_tokens,
                        model=error.model or self.model,
                    )
                if not error.recoverable:
                    raise
                self.history.append(f"{number}. unusable reply ({error.code})")
                if self._strike():
                    return Status.FAILED, error.code, self.notes_answer()
                continue

            try:
                action = act.parse_action(reply.action)
            except act.InvalidAction as error:
                self._record_reply(
                    number, "invalid", Verdict.INVALID, error.code, reply, step_started, browser
                )
                self.history.append(f"{number}. invalid reply ({error.code})")
                if self._strike():
                    return Status.FAILED, "too_many_strikes", self.notes_answer()
                continue

            verdict, note = self._execute(browser, action)
            self._record_reply(number, action.kind, verdict, note, reply, step_started, browser)
            outcome = f" ({note})" if note else ""
            self.history.append(f"{number}. {action.describe()} -> {str(verdict)}{outcome}")

            if action.kind == act.DONE:
                return Status.DONE, "", self.vault.unmask(action.text)
            if verdict == Verdict.BLOCKED and self._strike():
                return Status.FAILED, "too_many_strikes", self.notes_answer()

        return Status.LIMIT_REACHED, "max_steps", self.notes_answer()

    def _strike(self):
        self.strikes += 1
        return self.strikes >= self.limits.max_strikes

    def _limit_reached(self, browser, started):
        """Checked before every AI call, so no step is paid for past a limit."""
        limits = self.limits
        if selectors.get_task_status(self.task.school_id, self.task.pk) == Status.CANCELLED:
            return Status.CANCELLED, "cancelled_by_user", self.notes_answer()
        self.time_left = limits.max_seconds - (self.clock() - started)
        if self.time_left < TIME_RESERVE_SECONDS:
            return Status.LIMIT_REACHED, "max_seconds", self.notes_answer()
        if self.task.input_tokens >= limits.max_input_tokens:
            return Status.LIMIT_REACHED, "max_tokens", self.notes_answer()
        if self.task.cost_usd >= limits.max_cost_usd:
            return Status.LIMIT_REACHED, "max_cost", self.notes_answer()
        if budget.is_exhausted():
            return Status.LIMIT_REACHED, "monthly_budget", self.notes_answer()
        if browser.pages_visited > limits.max_pages:
            return Status.LIMIT_REACHED, "max_pages", self.notes_answer()
        return None

    def _page_text(self, browser):
        url = browser.current_url
        if not url.startswith(("http://", "https://")):
            raw = {"elements": [], "text": ["(Blank page. Use goto to open a website.)"]}
        else:
            try:
                raw = browser.run_script(EXTRACT_SCRIPT, script_arg(self.limits.max_page_chars))
            except BrowserActionError:
                raw = {"url": url, "elements": [], "text": ["(The page could not be read.)"]}
            if not isinstance(raw, dict):
                raw = {"url": url, "elements": [], "text": []}
        return format_snapshot(raw, max_chars=self.limits.max_page_chars)

    def _execute(self, browser, action):
        kind = action.kind
        try:
            if kind == act.GOTO:
                if PLACEHOLDER.search(action.url):
                    return Verdict.BLOCKED, "personal_data_in_url"
                try:
                    check_navigation(action.url)
                except BlockedUrl as error:
                    return Verdict.BLOCKED, error.code
                browser.goto(action.url)
            elif kind == act.CLICK:
                browser.click(action.ref)
            elif kind == act.TYPE:
                browser.type(action.ref, self.vault.unmask(action.text))
            elif kind == act.SELECT:
                browser.select(action.ref, self.vault.unmask(action.text))
            elif kind == act.SCROLL:
                browser.scroll(action.direction)
            elif kind == act.BACK:
                browser.back()
            elif kind == act.WAIT:
                browser.wait()
            elif kind == act.EXTRACT:
                self.notes = [*self.notes, action.text[:300]][-MAX_NOTES:]
        except BrowserActionError as error:
            return Verdict.FAILED, error.code

        # A click or a redirect can land on an address or domain we don't allow.
        url = browser.current_url
        if url.startswith(("http://", "https://")):
            try:
                check_navigation(url)
            except BlockedUrl as error:
                with suppress(BrowserActionError):
                    browser.blank()
                return Verdict.BLOCKED, f"landed_on_{error.code}"
        return Verdict.OK, ""

    def _record_reply(self, number, action, verdict, note, reply, step_started, browser):
        self._record(
            number,
            action,
            verdict,
            note,
            step_started,
            browser,
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            model=reply.model,
        )

    def _record(
        self,
        number,
        action,
        verdict,
        note,
        step_started,
        browser,
        *,
        input_tokens,
        output_tokens,
        model,
    ):
        step = services.record_step(
            self.task,
            number=number,
            action=action,
            domain=domain_of(browser.current_url),
            verdict=verdict,
            note=note,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=max(0, int((self.clock() - step_started) * 1000)),
            model=model,
        )
        if self.on_step is not None:
            self.on_step(step)
