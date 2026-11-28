"""Stand-ins for the AI provider and the browser, so the loop is tested without either."""

from apps.integrations.ai.agent_provider import AgentReply
from apps.integrations.browser.playwright_browser import BrowserActionError

PUBLIC_IP = "93.184.216.34"


def fake_resolve(host):
    # "inside.test" stands for a public-looking name that points at a private address.
    return {"10.0.0.7"} if host == "inside.test" else {PUBLIC_IP}


def reply(action, **fields):
    return {
        "reason": "test",
        "action": action,
        "ref": fields.get("ref"),
        "text": fields.get("text"),
        "url": fields.get("url"),
        "direction": fields.get("direction"),
    }


class ScriptedProvider:
    """Hands back the given replies in order (then "wait") and keeps what it was sent."""

    def __init__(self, replies, *, tokens=(100, 10)):
        self.replies = list(replies)
        self.calls = []
        self.tokens = tokens

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        action = self.replies.pop(0) if self.replies else reply("wait")
        return AgentReply(
            action=action,
            input_tokens=self.tokens[0],
            output_tokens=self.tokens[1],
            model="gpt-4o-mini",
        )

    def everything_sent(self):
        return "\n".join(
            f"{call['goal']}\n{call['history']}\n{call['notes']}\n{call['page']}"
            for call in self.calls
        )


class FakeBrowser:
    def __init__(self, *, raw=None, click_to=None):
        self.url = "about:blank"
        self.pages_visited = 0
        self.visited = []
        self.typed = []
        self.clicked = []
        self.closed = False
        self.click_to = click_to
        self.raw = raw or {
            "url": "https://example.com/",
            "title": "Example",
            "elements": [{"ref": "e1", "role": "textbox", "name": "Phone", "type": "tel"}],
            "text": ["Welcome"],
        }

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.closed = True
        return False

    @property
    def current_url(self):
        return self.url

    def goto(self, url):
        self.url = url
        self.visited.append(url)
        self.pages_visited += 1

    def blank(self):
        self.url = "about:blank"

    def run_script(self, script, arg):
        return self.raw

    def click(self, ref):
        if ref == "e404":
            raise BrowserActionError("element_not_found")
        self.clicked.append(ref)
        if self.click_to:
            self.goto(self.click_to)

    def type(self, ref, text):
        self.typed.append((ref, text))

    def select(self, ref, option):
        self.typed.append((ref, option))

    def scroll(self, direction):
        pass

    def back(self):
        pass

    def wait(self):
        pass
