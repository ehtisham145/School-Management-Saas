import pytest

from apps.browser_agent import actions as act
from apps.browser_agent.snapshot import (
    SENSITIVE_KEYWORDS,
    format_snapshot,
    has_sensitive_keyword,
    script_arg,
    url_without_query,
)


def test_private_fields_never_show_their_value():
    raw = {
        "url": "https://example.com/login?session=abc123#top",
        "title": "Sign in",
        "elements": [
            {"ref": "e1", "role": "textbox", "name": "Email", "type": "email", "value": "x@y.z"},
            {
                "ref": "e2",
                "role": "textbox",
                "name": "Password",
                "type": "password",
                "sensitive": False,
                "value": "hunter2",
            },
            {
                "ref": "e3",
                "role": "textbox",
                "name": "Code",
                "type": "text",
                "sensitive": True,
                "value": "839201",
            },
            {"ref": "e4", "role": "textbox", "name": "Token", "type": "hidden", "value": "tok"},
            {"ref": "e5", "role": "button", "name": "Sign in", "type": "submit"},
        ],
        "text": ["Welcome back"],
    }

    text = format_snapshot(raw, max_chars=5000)

    assert "hunter2" not in text
    assert "839201" not in text
    assert "tok" not in text.replace("Token", "")
    assert "abc123" not in text
    assert '[e2] textbox "Password" (private field: the user fills it in)' in text
    assert '[e1] textbox "Email" value="x@y.z"' in text
    assert "Address: https://example.com/login" in text


def test_snapshot_lists_options_checks_and_text_once():
    raw = {
        "url": "https://example.com/",
        "title": 'A "quoted" title',
        "elements": [
            {"ref": "e1", "role": "select", "name": "Grade", "options": ["7", "8"], "value": "7"},
            {"ref": "e2", "role": "checkbox", "name": "Agree", "checked": False},
        ],
        "text": ["# Heading", "Same line", "Same line", "Other"],
    }

    text = format_snapshot(raw, max_chars=5000)

    assert "options: 7, 8" in text
    assert '[e2] checkbox "Agree" unchecked' in text
    assert text.count("Same line") == 1
    assert "Title: A 'quoted' title" in text


def test_snapshot_is_cut_to_the_limit():
    # Different lines: repeated lines are merged into one, so they wouldn't reach the limit.
    lines = [f"line {number} " + "word " * 50 for number in range(50)]
    raw = {"url": "https://example.com/", "title": "T", "elements": [], "text": lines}

    text = format_snapshot(raw, max_chars=600)

    assert len(text) <= 600 + len("\n[page text cut here]")
    assert text.endswith("[page text cut here]")


@pytest.mark.parametrize(
    "described",
    [
        "card_number",
        "cardNumber",
        "Card number",
        "cvv",
        "CVC",
        "otp_code",
        "otpCode",
        "PIN",
        "iban",
        "National ID",
        "iqama_no",
        "new-password",
        "access_token",
        "كلمة المرور",
        "رقم الهوية",
        "رقم الإقامة",
        "رقم البطاقة",
        "رمز التحقق",
        "الآيبان",
    ],
)
def test_sensitive_keywords_in_english_and_arabic(described):
    assert has_sensitive_keyword(described)


@pytest.mark.parametrize(
    "described", ["shipping_address", "spinner", "discard_reason", "Email", "Full name", "المدينة"]
)
def test_ordinary_fields_are_not_sensitive(described):
    assert not has_sensitive_keyword(described)


@pytest.mark.parametrize(
    "item",
    [
        {"role": "textbox", "name": "Number", "type": "text", "hints": "card_number"},
        {"role": "textbox", "name": "", "type": "text", "hints": "cvv"},
        {"role": "textbox", "name": "Code", "type": "text", "hints": "otp"},
        {"role": "textbox", "name": "الرقم", "type": "text", "hints": "رقم الهوية"},
        {"role": "textbox", "name": "x", "type": "text", "autocomplete": "one-time-code"},
    ],
)
def test_python_marks_sensitive_fields_even_when_the_page_script_did_not(item):
    raw = {
        "url": "https://example.com/",
        "title": "T",
        "elements": [{**item, "ref": "e1", "sensitive": False, "value": "4111111111111111"}],
        "text": [],
    }

    text = format_snapshot(raw, max_chars=5000)

    assert "4111111111111111" not in text
    assert text.count("(private field: the user fills it in)") == 1


def test_a_link_with_a_keyword_in_its_name_is_not_a_field():
    raw = {"elements": [{"ref": "e1", "role": "link", "name": "Card games"}], "text": []}
    assert "private field" not in format_snapshot(raw, max_chars=5000)


def test_names_are_cut_to_80_characters():
    raw = {"elements": [{"ref": "e1", "role": "button", "name": "x" * 200}], "text": []}
    text = format_snapshot(raw, max_chars=5000)
    assert f'"{"x" * 80}"' in text
    assert "x" * 81 not in text


def test_an_element_without_a_name_gets_a_hint():
    raw = {"elements": [{"ref": "e1", "role": "textbox", "name": "", "hint": "input email"}]}
    assert '[e1] textbox "(no label: input email)"' in format_snapshot(raw, max_chars=5000)


def test_the_page_script_gets_the_same_keyword_list():
    arg = script_arg(1234)
    assert arg["keywords"] == list(SENSITIVE_KEYWORDS)
    assert (arg["maxChars"], arg["nameLimit"]) == (1234, 80)


def test_url_without_query():
    assert url_without_query("https://a.com/x/y?q=1#f") == "https://a.com/x/y"
    assert url_without_query("") == ""


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ({"action": "click", "ref": "e12"}, act.Action(kind="click", ref="e12")),
        (
            {"action": "type", "ref": "e3", "text": "{PHONE_1}"},
            act.Action(kind="type", ref="e3", text="{PHONE_1}"),
        ),
        (
            {"action": "goto", "url": "https://example.com"},
            act.Action(kind="goto", url="https://example.com"),
        ),
        ({"action": "scroll", "direction": "up"}, act.Action(kind="scroll", direction="up")),
        ({"action": "done", "text": "Opens at 9"}, act.Action(kind="done", text="Opens at 9")),
        ({"action": "back"}, act.Action(kind="back")),
    ],
)
def test_valid_actions_are_parsed(reply, expected):
    assert act.parse_action(reply) == expected


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        ("click e1", "not_an_object"),
        ({"action": "eval"}, "unknown_action"),
        ({"action": "click", "ref": "#login"}, "bad_ref"),
        ({"action": "click", "ref": 'e1"] , [x'}, "bad_ref"),
        ({"action": "type", "ref": "e1", "text": "  "}, "missing_text"),
        ({"action": "done"}, "missing_text"),
        ({"action": "goto"}, "missing_url"),
        ({"action": "scroll", "direction": "left"}, "bad_direction"),
        ({"action": "extract", "text": "x" * 2001}, "text_too_long"),
    ],
)
def test_invalid_actions_are_refused(reply, code):
    with pytest.raises(act.InvalidAction) as error:
        act.parse_action(reply)
    assert error.value.code == code


def test_schema_is_strict():
    schema = act.ACTION_SCHEMA
    assert schema["additionalProperties"] is False
    assert sorted(schema["required"]) == sorted(schema["properties"])
    assert schema["properties"]["action"]["enum"] == list(act.ACTIONS)
