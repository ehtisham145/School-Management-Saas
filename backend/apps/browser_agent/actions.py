"""The closed list of actions the AI may choose, and the check on what it sends back."""

import re
from dataclasses import dataclass

GOTO = "goto"
CLICK = "click"
TYPE = "type"
SELECT = "select"
SCROLL = "scroll"
BACK = "back"
WAIT = "wait"
EXTRACT = "extract"
DONE = "done"

ACTIONS = (GOTO, CLICK, TYPE, SELECT, SCROLL, BACK, WAIT, EXTRACT, DONE)
NEEDS_REF = frozenset({CLICK, TYPE, SELECT})
NEEDS_TEXT = frozenset({TYPE, SELECT, EXTRACT, DONE})
REF = re.compile(r"^e\d{1,4}$")
MAX_TEXT = 2000

# Strict JSON schema for the provider: every key present, unused ones null.
ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reason": {"type": "string", "description": "One short sentence: why this step."},
        "action": {"type": "string", "enum": list(ACTIONS)},
        "ref": {"type": ["string", "null"], "description": "Element ref such as e12."},
        "text": {
            "type": ["string", "null"],
            "description": "Text to type, option to select, note to keep, or the final answer.",
        },
        "url": {"type": ["string", "null"], "description": "Full http(s) URL for goto."},
        "direction": {"type": ["string", "null"], "enum": ["up", "down", None]},
    },
    "required": ["reason", "action", "ref", "text", "url", "direction"],
}


class InvalidAction(ValueError):
    """The AI's reply isn't a usable action. `code` is safe to log."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Action:
    kind: str
    ref: str = ""
    text: str = ""
    url: str = ""
    direction: str = "down"

    def describe(self):
        """A short line for the history sent back to the AI. Only masked values appear."""
        if self.kind == GOTO:
            return f"goto {self.url[:200]}"
        if self.kind == CLICK:
            return f"click {self.ref}"
        if self.kind in (TYPE, SELECT):
            return f'{self.kind} {self.ref} "{self.text[:80]}"'
        if self.kind == SCROLL:
            return f"scroll {self.direction}"
        if self.kind == EXTRACT:
            return f'note "{self.text[:120]}"'
        return self.kind


def parse_action(reply) -> Action:
    if not isinstance(reply, dict):
        raise InvalidAction("not_an_object")
    kind = reply.get("action")
    if kind not in ACTIONS:
        raise InvalidAction("unknown_action")

    ref = str(reply.get("ref") or "").strip()
    text = str(reply.get("text") or "")
    url = str(reply.get("url") or "").strip()
    direction = reply.get("direction") or "down"

    if kind in NEEDS_REF and not REF.match(ref):
        raise InvalidAction("bad_ref")
    if kind in NEEDS_TEXT and not text.strip():
        raise InvalidAction("missing_text")
    if len(text) > MAX_TEXT:
        raise InvalidAction("text_too_long")
    if kind == GOTO and not url:
        raise InvalidAction("missing_url")
    if direction not in ("up", "down"):
        raise InvalidAction("bad_direction")
    return Action(kind=kind, ref=ref, text=text, url=url, direction=direction)
