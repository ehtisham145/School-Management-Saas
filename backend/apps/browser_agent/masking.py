"""Masks personal data before page text or the goal goes to the AI provider.

Emails, phone numbers, national IDs / Iqama numbers, IBANs, card numbers and long account
numbers become placeholders such as {EMAIL_1}. The real values stay in a MaskVault in this
process for one task, and are put back only when the agent acts on our server.

This catches structured data well and free-text names of other people poorly; the privacy
notice says so (docs/browser-agent.md §5). Python's \\d also matches Arabic-Indic digits."""

import re

PLACEHOLDER = re.compile(r"\{([A-Z]+)_(\d+)\}")

# Order matters: each pattern runs on the text the earlier ones left. EMAIL must stay first.
_PATTERNS = (
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("IBAN", re.compile(r"(?<![\w])SA\d{2}(?:[ ]?[A-Z0-9]){20}(?![\w])", re.IGNORECASE)),
    ("CARD", re.compile(r"(?<![\d+])\d(?:[ -]?\d){12,18}(?!\d)")),
    ("PHONE", re.compile(r"(?<![\d+])(?:(?:\+|00)?966[ -]?|0)?5(?:[ -]?\d){8}(?!\d)")),
    ("PHONE", re.compile(r"(?<![\d+])(?:(?:\+|00)?966[ -]?|0)1[1-7](?:[ -]?\d){7}(?!\d)")),
    ("ID", re.compile(r"(?<!\d)[12]\d{9}(?!\d)")),
    ("PHONE", re.compile(r"(?<![\d\w])\+\d(?:[ -]?\d){7,14}(?!\d)")),
    ("NUMBER", re.compile(r"(?<!\d)\d{8,}(?!\d)")),
)


def _luhn_ok(value):
    digits = [int(char) for char in value if char.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


class MaskVault:
    """Maps placeholders to real values for one task. Same value, same placeholder."""

    def __init__(self, *, known=()):
        self._by_placeholder = {}
        self._by_value = {}
        self._counts = {}
        # Values we know are personal, such as the teacher's own name and email.
        values = {value.strip() for value in known if value and len(value.strip()) > 2}
        self._known = sorted(values, key=len, reverse=True)

    def _placeholder(self, kind, value):
        key = (kind, value)
        if key not in self._by_value:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            placeholder = f"{{{kind}_{self._counts[kind]}}}"
            self._by_value[key] = placeholder
            self._by_placeholder[placeholder] = value
        return self._by_value[key]

    def mask(self, text):
        if not text:
            return ""
        # A page could print "{NAME_1}" to make the agent type a real value; defuse it.
        text = PLACEHOLDER.sub(lambda match: f"({match.group(1)}_{match.group(2)})", text)
        # Emails first, so a name inside an address doesn't split it.
        email_kind, email_pattern = _PATTERNS[0]
        text = self._apply(email_kind, email_pattern, text)
        for value in self._known:
            pattern = re.compile(rf"(?<!\w){re.escape(value)}(?!\w)", re.IGNORECASE)
            text = self._apply("NAME", pattern, text)
        for kind, pattern in _PATTERNS[1:]:
            text = self._apply(kind, pattern, text)
        return text

    def _apply(self, kind, pattern, text):
        return pattern.sub(lambda match: self._replace(kind, match.group(0)), text)

    def _replace(self, kind, value):
        if kind == "CARD" and not _luhn_ok(value):
            return value
        return self._placeholder(kind, value)

    def unmask(self, text):
        if not text:
            return text or ""
        return PLACEHOLDER.sub(
            lambda match: self._by_placeholder.get(match.group(0), match.group(0)), text
        )

    def __len__(self):
        return len(self._by_placeholder)
