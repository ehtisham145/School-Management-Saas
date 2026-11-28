"""Turns a page into short text for the AI: a numbered list of the elements it can use, and
the visible text. Never HTML.

Each usable element gets a `data-agent-ref="eN"` attribute, and actions point at those refs,
not at free CSS selectors (the same idea as Playwright MCP's element refs).

- Only what a person can see: text that is hidden from people but readable by a machine
  (opacity ~0, tiny font, off the page, same colour as its background, pushed out by
  text-indent, clipped to nothing) is left out, for elements and for each piece of text.
- Names prefer what is on screen (label, text) over aria-label/title/placeholder, which
  people don't see, and are cut to 80 characters.
- Sensitive fields (password, card, CVV, OTP, PIN, IBAN, national ID, Iqama...; English and
  Arabic, SENSITIVE_KEYWORDS) are listed without their values. The page script decides
  first and Python checks again.

Best effort, not a security boundary: background images, clip-path, transforms, overlays,
canvas/SVG text and pseudo-elements aren't analysed, and the page's own scripts could
change the DOM functions this script calls. Masking (agent.py) runs on the result anyway."""

import re
from urllib.parse import urlsplit, urlunsplit

MAX_ELEMENTS = 150
NAME_LIMIT = 80
PRIVATE_LABEL = " (private field: the user fills it in)"

# One list for the page script and for Python. ASCII entries match whole words of a
# field's name/id/label/placeholder ("card_number", "cardNumber", "Card number" all have
# the word "card"; "shipping" doesn't have "pin"). Arabic entries match anywhere.
SENSITIVE_KEYWORDS = (
    "card",
    "cardnumber",
    "ccnumber",
    "cvv",
    "cvc",
    "csc",
    "otp",
    "pin",
    "pincode",
    "passcode",
    "password",
    "passwd",
    "pwd",
    "iban",
    "national id",
    "nationalid",
    "iqama",
    "ssn",
    "token",
    "secret",
    "security code",
    "كلمة المرور",
    "كلمة السر",
    "الرقم السري",
    "رمز",
    "رمز التحقق",
    "الهوية",
    "هوية",
    "الإقامة",
    "إقامة",
    "اقامة",
    "البطاقة",
    "بطاقة",
    "الآيبان",
    "آيبان",
    "ايبان",
)

# Runs in the page. Takes the dict from script_arg() and returns plain data.
EXTRACT_SCRIPT = r"""
({maxElements, maxChars, keywords, nameLimit}) => {
  const clean = (value, limit) => (value || "").replace(/\s+/g, " ").trim().slice(0, limit);

  // ------------------------------------------------------------ what a person can see
  const parseColor = (value) => {
    const match = /rgba?\(([^)]+)\)/.exec(value || "");
    if (!match) return null;
    const p = match[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  };
  const backgroundOf = (el) => {
    for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.backgroundImage && style.backgroundImage !== "none") return null;
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0.5) return color;
    }
    return {r: 255, g: 255, b: 255, a: 1};
  };
  const sameColour = (el, style) => {
    const fg = parseColor(style.color);
    if (!fg) return false;
    if (fg.a < 0.1) return true;
    const bg = backgroundOf(el);
    if (!bg) return false;
    return Math.abs(fg.r - bg.r) + Math.abs(fg.g - bg.g) + Math.abs(fg.b - bg.b) < 30;
  };

  const ownHidden = (el) => {
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" ||
        style.visibility === "collapse" || style.contentVisibility === "hidden") return true;
    if (parseFloat(style.opacity) < 0.1) return true;
    if (style.display === "contents") return false;
    const box = el.getBoundingClientRect();
    const clipped = /hidden|clip/.test(style.overflow + style.overflowX + style.overflowY);
    if (clipped && (box.width < 2 || box.height < 2)) return true;
    // Entirely above or left of the page: nobody can scroll there.
    if (box.right + window.scrollX < 0 || box.bottom + window.scrollY < 0) return true;
    return false;
  };
  const hiddenCache = new Map();
  const isHidden = (el) => {
    if (!el || el.nodeType !== 1 || el === document.documentElement) return false;
    if (!hiddenCache.has(el)) hiddenCache.set(el, ownHidden(el) || isHidden(el.parentElement));
    return hiddenCache.get(el);
  };
  const textCache = new Map();
  const textHidden = (el) => {
    if (!textCache.has(el)) {
      let hidden = isHidden(el);
      if (!hidden) {
        const style = getComputedStyle(el);
        hidden = parseFloat(style.fontSize) < 6 || parseFloat(style.textIndent) < -500 ||
          sameColour(el, style);
      }
      textCache.set(el, hidden);
    }
    return textCache.get(el);
  };
  const skipText = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"]);
  const visibleText = (root, limit) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const parts = [];
    let length = 0;
    while (walker.nextNode()) {
      const parent = walker.currentNode.parentElement;
      if (!parent || skipText.has(parent.tagName) || textHidden(parent)) continue;
      const value = clean(walker.currentNode.nodeValue, limit);
      if (!value) continue;
      parts.push(value);
      length += value.length + 1;
      if (length > limit) break;
    }
    return clean(parts.join(" "), limit);
  };
  const boxVisible = (el) => {
    const box = el.getBoundingClientRect();
    return box.width >= 2 && box.height >= 2 && !isHidden(el);
  };

  // ------------------------------------------------------------ sensitive fields
  const words = (value) => " " + (value || "").replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).join(" ") + " ";
  const ascii = (value) => /^[\x00-\x7f]*$/.test(value);
  const hasKeyword = (value) => {
    const flat = (value || "").replace(/\s+/g, " ");
    const padded = words(value);
    return keywords.some((k) => ascii(k) ? padded.includes(" " + k + " ") : flat.includes(k));
  };

  // ------------------------------------------------------------ elements
  for (const old of document.querySelectorAll("[data-agent-ref]")) {
    old.removeAttribute("data-agent-ref");
  }
  const usable = 'a[href],button,input,select,textarea,summary,[role=button],[role=link],' +
    '[role=checkbox],[role=radio],[role=tab],[role=menuitem],[role=option],' +
    '[contenteditable]:not([contenteditable=false])';
  const roles = {
    A: "link", BUTTON: "button", SELECT: "select", TEXTAREA: "textbox", SUMMARY: "button",
  };
  const elements = [];
  let count = 0;
  for (const el of document.querySelectorAll(usable)) {
    if (elements.length >= maxElements) break;
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (el.disabled || (el.tagName === "INPUT" && type === "hidden")) continue;
    const label = el.labels && el.labels.length ? el.labels[0] : null;
    const toggle = el.tagName === "INPUT" && (type === "checkbox" || type === "radio");
    // A styled checkbox often hides the real input behind its visible label.
    if (!boxVisible(el) && !(toggle && label && boxVisible(label))) continue;

    const editable = el.isContentEditable && !["INPUT", "TEXTAREA"].includes(el.tagName);
    let role = el.getAttribute("role") || roles[el.tagName] || (editable ? "textbox" : "generic");
    if (el.tagName === "INPUT") {
      role = toggle ? type
        : ["submit", "button", "reset", "image"].includes(type) ? "button" : "textbox";
    }
    const field = ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || editable;

    const labelText = label ? visibleText(label, nameLimit) : "";
    let name = labelText;
    if (!name && !field) name = visibleText(el, nameLimit);
    if (!name && role === "button" && el.tagName === "INPUT") name = el.value;
    name = name || el.getAttribute("placeholder") || el.getAttribute("aria-label") ||
      el.getAttribute("title") || el.getAttribute("alt") || "";

    const autocomplete = (el.getAttribute("autocomplete") || "").toLowerCase();
    const hints = [
      el.getAttribute("name"), el.id, labelText, el.getAttribute("placeholder"),
      el.getAttribute("aria-label"), el.getAttribute("title"),
    ].filter(Boolean).join(" | ").slice(0, 300);
    const sensitive = type === "password" || autocomplete.includes("password") ||
      autocomplete.includes("one-time-code") || autocomplete.startsWith("cc-") ||
      (field && hasKeyword(hints));

    count += 1;
    const ref = "e" + count;
    el.setAttribute("data-agent-ref", ref);
    const item = {
      ref, role, name: clean(name, nameLimit), type, sensitive, autocomplete,
      hint: el.tagName.toLowerCase() + (type ? " " + type : ""),
    };
    if (field) item.hints = hints;
    if (!sensitive) {
      if (el.tagName === "SELECT") item.value = clean(el.selectedOptions[0]?.text, 100);
      else if (editable) item.value = visibleText(el, 200);
      else if (role === "textbox") item.value = clean(el.value, 200);
    }
    if (toggle) item.checked = !!el.checked;
    if (el.tagName === "SELECT") {
      item.options = Array.from(el.options).slice(0, 20).map((o) => clean(o.text, 60));
    }
    elements.push(item);
  }

  // ------------------------------------------------------------ text
  const text = [];
  let total = 0;
  const blocks = "h1,h2,h3,h4,p,li,td,th,dt,dd,blockquote,pre,figcaption";
  for (const el of document.querySelectorAll(blocks)) {
    if (el.closest("nav,footer,aside,[aria-hidden=true]") || isHidden(el)) continue;
    const value = visibleText(el, 500);
    if (!value) continue;
    const tag = el.tagName.toLowerCase();
    text.push(tag[0] === "h" ? "#".repeat(Number(tag[1])) + " " + value : value);
    total += value.length;
    if (total > maxChars) break;
  }
  return {url: location.href, title: clean(document.title, 200), elements, text};
}
"""

SENSITIVE_TYPES = frozenset({"password", "hidden"})
FIELD_ROLES = frozenset({"textbox", "select"})
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
_NOT_WORD = re.compile(r"[^a-z0-9]+")


def script_arg(max_chars):
    """The argument EXTRACT_SCRIPT takes."""
    return {
        "maxElements": MAX_ELEMENTS,
        "maxChars": max_chars,
        "keywords": list(SENSITIVE_KEYWORDS),
        "nameLimit": NAME_LIMIT,
    }


def has_sensitive_keyword(value):
    """Same rule as hasKeyword() in the page script."""
    value = str(value or "")
    padded = " " + " ".join(filter(None, _NOT_WORD.split(_CAMEL.sub(r"\1 \2", value).lower())))
    padded += " "
    flat = " ".join(value.split())
    for keyword in SENSITIVE_KEYWORDS:
        if keyword.isascii():
            if f" {keyword} " in padded:
                return True
        elif keyword in flat:
            return True
    return False


def is_sensitive(item):
    """The page script's verdict, checked again here, so a value never leaks if it missed."""
    if item.get("sensitive"):
        return True
    if str(item.get("type") or "").lower() in SENSITIVE_TYPES:
        return True
    autocomplete = str(item.get("autocomplete") or "").lower()
    if "password" in autocomplete or "one-time-code" in autocomplete:
        return True
    if autocomplete.startswith("cc-"):
        return True
    is_field = item.get("role") in FIELD_ROLES or "value" in item or "hints" in item
    described = f"{item.get('name') or ''} {item.get('hints') or ''}"
    return is_field and has_sensitive_keyword(described)


def _one_line(value, limit):
    return " ".join(str(value or "").split())[:limit].replace('"', "'")


def url_without_query(url):
    """Path kept, query and fragment dropped: they often carry tokens or personal data."""
    try:
        parts = urlsplit(url or "")
    except ValueError:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))[:300]


def format_snapshot(raw, *, max_chars):
    """Plain text for the prompt, at most max_chars long."""
    lines = [
        f"Title: {_one_line(raw.get('title'), 200)}",
        f"Address: {url_without_query(raw.get('url'))}",
        "Elements:",
    ]
    for item in (raw.get("elements") or [])[:MAX_ELEMENTS]:
        ref = _one_line(item.get("ref"), 10)
        name = _one_line(item.get("name"), NAME_LIMIT)
        if not name:
            hint = _one_line(item.get("hint") or item.get("role") or "element", 30)
            name = f"(no label: {hint})"
        line = f'[{ref}] {_one_line(item.get("role"), 20)} "{name}"'
        if is_sensitive(item):
            line += PRIVATE_LABEL
        elif item.get("value"):
            line += f' value="{_one_line(item["value"], 200)}"'
        if "checked" in item:
            line += " checked" if item["checked"] else " unchecked"
        if item.get("options"):
            options = ", ".join(_one_line(option, 60) for option in item["options"][:20])
            line += f" options: {options}"
        lines.append(line)

    lines.append("Text:")
    previous = None
    for value in raw.get("text") or []:
        value = _one_line(value, 500)
        if value and value != previous:
            lines.append(value)
        previous = value

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0] + "\n[page text cut here]"
    return text
