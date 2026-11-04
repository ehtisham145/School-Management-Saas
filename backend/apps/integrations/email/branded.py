# ruff: noqa: E501  (email HTML is inline-styled, so its lines are long)
"""
Branded transactional email helper.

One consistent header, footer and styling for every outbound email. Callers build a
small HTML body from the block helpers and call send_branded_email(). A plain-text
fallback is generated automatically.

Trust rule: `html` arguments, `heading`, `intro` and `preheader` are trusted markup.
Anything a user typed, including names, must go through user_text() before it is placed
in them. detail_table() and code_box() escape their own values.
"""

from __future__ import annotations

import base64
import html as html_lib
import logging
import re
from datetime import date
from email.mime.image import MIMEImage
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape, strip_tags

logger = logging.getLogger(__name__)

LOGO_FILE = Path(__file__).parent / "assets" / "logo-on-dark.png"
LOGO_CID = "lessonlab-logo"

# Email clients can't read CSS variables, so these repeat the tokens in
# frontend/src/app/globals.css. Keep the two in step.
NAVY = "#1e3a5f"
ON_NAVY_SOFT = "#c3d4e6"
ORANGE = "#f5781e"
# The darker orange (orange-text): white text on the brighter one isn't readable.
CTA = "#b9500c"

INK = "#0f172a"
TEXT = "#334155"
MUTED = "#475569"
SUBTLE = "#64748b"
BORDER = "#e2e8f0"
SURFACE = "#f8fafc"
CANVAS = "#f1f5f9"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "'SFMono-Regular',Menlo,Consolas,'Courier New',monospace"

_TONES = {
    # tone: (background, border, text)
    "neutral": (SURFACE, BORDER, TEXT),
    "info": ("#e1eaf3", ON_NAVY_SOFT, NAVY),
    "warning": ("#fef0e5", "#fbd5b5", "#92400e"),
    "danger": ("#fef2f2", "#fecaca", "#991b1b"),
    "success": ("#ecfdf5", "#a7f3d0", "#065f46"),
}


def _brand() -> dict:
    """Brand identity pulled from settings."""
    return {
        "name": settings.COMPANY_NAME,
        "label": settings.BRAND_HEADER_LABEL,
        "website": settings.COMPANY_WEBSITE,
        "support": settings.SUPPORT_EMAIL,
        "address": settings.COMPANY_ADDRESS,
        # Attached to the email unless a public URL is set, so it never depends on the
        # site being reachable from the mail provider's servers.
        "logo": settings.BRAND_LOGO_URL or f"cid:{LOGO_CID}",
        "logo_w": settings.BRAND_LOGO_WIDTH,
        "logo_h": settings.BRAND_LOGO_HEIGHT,
        "year": date.today().year,
    }


def user_text(value: str) -> str:
    """Escape user-supplied text and keep its line breaks."""
    return escape(value or "").replace("\n", "<br>")


def paragraph(html: str, *, muted: bool = False, spacing: int = 16) -> str:
    color, size = (MUTED, 13) if muted else (TEXT, 15)
    return (
        f'<p style="margin:0 0 {spacing}px;font-size:{size}px;line-height:1.6;color:{color};">'
        f"{html}</p>"
    )


def code_box(code: str, *, label: str = "Your verification code") -> str:
    """Large, easy-to-copy one-time code."""
    return f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px;">
        <tr><td align="center" style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:18px 16px;">
          <div style="font-size:12px;font-weight:600;color:{MUTED};letter-spacing:0.4px;text-transform:uppercase;">{label}</div>
          <div style="margin-top:8px;font-family:{MONO};font-size:30px;font-weight:700;color:{INK};letter-spacing:8px;">{escape(code)}</div>
        </td></tr>
      </table>"""


def buttons(items: list[tuple[str, str, str]]) -> str:
    """Row of buttons plus a link fallback. items = (label, url, variant), where variant
    is 'primary' (orange), 'neutral' (navy), 'success' or 'danger'."""
    colours = {"primary": CTA, "neutral": NAVY, "success": "#047857", "danger": "#b91c1c"}
    cells = ""
    for i, (label, url, variant) in enumerate(items):
        pad = "padding-left:8px;" if i else ""
        bg = colours.get(variant, CTA)
        cells += (
            f'<td style="{pad}vertical-align:top;">'
            f'<a href="{escape(url)}" target="_blank" style="display:inline-block;padding:10px 20px;'
            f"font-size:14px;font-weight:600;line-height:1;color:#ffffff;text-decoration:none;"
            f'border-radius:6px;background:{bg};">{label}</a></td>'
        )
    links = "<br>".join(
        f'{label}: <a href="{escape(url)}" style="color:{NAVY};word-break:break-all;">{escape(url)}</a>'
        for label, url, _ in items
    )
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:4px 0 14px;">'
        f"<tr>{cells}</tr></table>"
        f'<p style="margin:0;font-size:12px;color:{SUBTLE};line-height:1.6;">'
        f"If the buttons don't work, copy these links into your browser:<br>{links}</p>"
    )


def detail_table(rows: list[tuple[str, str]], *, mono: tuple[str, ...] = ()) -> str:
    """Label / value rows. Values are escaped; labels listed in mono use a monospace font."""
    body = ""
    last = len(rows) - 1
    for i, (label, value) in enumerate(rows):
        border = "" if i == last else f"border-bottom:1px solid {BORDER};"
        family = f"font-family:{MONO};" if label in mono else ""
        body += (
            f"<tr>"
            f'<td style="padding:11px 16px;{border}font-size:13px;color:{MUTED};width:38%;vertical-align:top;">{escape(label)}</td>'
            f'<td style="padding:11px 16px;{border}font-size:14px;font-weight:600;color:{INK};{family}word-break:break-word;">{escape(str(value))}</td>'
            f"</tr>"
        )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:0 0 16px;border:1px solid {BORDER};border-radius:8px;border-collapse:separate;">{body}</table>'
    )


def notice(html: str, *, tone: str = "neutral", title: str = "") -> str:
    """Bordered callout for expiry warnings, reasons and notes."""
    bg, border, color = _TONES.get(tone, _TONES["neutral"])
    head = f'<div style="font-weight:600;margin-bottom:4px;">{title}</div>' if title else ""
    return (
        f'<div style="margin:0 0 16px;background:{bg};border:1px solid {border};border-radius:8px;'
        f'padding:12px 16px;font-size:14px;line-height:1.55;color:{color};">{head}{html}</div>'
    )


def checklist(items: list[str], *, title: str = "") -> str:
    head = (
        f'<div style="margin:0 0 8px;font-size:13px;font-weight:600;color:{INK};">{title}</div>'
        if title
        else ""
    )
    rows = "".join(
        f'<tr><td style="padding:3px 10px 3px 0;vertical-align:top;color:{NAVY};font-size:14px;">&#10003;</td>'
        f'<td style="padding:3px 0;font-size:14px;line-height:1.5;color:{TEXT};">{item}</td></tr>'
        for item in items
    )
    return (
        f'<div style="margin:0 0 16px;">{head}'
        f'<table role="presentation" cellpadding="0" cellspacing="0">{rows}</table></div>'
    )


def _footer_contact(b: dict) -> str:
    contact = []
    if b["support"]:
        contact.append(
            f'Need help? <a href="mailto:{escape(b["support"])}" '
            f'style="color:{NAVY};text-decoration:none;">{escape(b["support"])}</a>'
        )
    if b["website"]:
        shown = re.sub(r"^https?://", "", b["website"])
        contact.append(
            f'<a href="{escape(b["website"])}" style="color:{NAVY};text-decoration:none;">'
            f"{escape(shown)}</a>"
        )
    lines = ([escape(b["address"])] if b["address"] else []) + (
        ["&nbsp;·&nbsp;".join(contact)] if contact else []
    )
    if not lines:
        return ""
    return (
        f'<p style="margin:0 0 10px;font-size:12px;color:{MUTED};line-height:1.6;">'
        f"{'<br>'.join(lines)}</p>"
    )


def render_branded_email(
    *,
    heading: str,
    body_html: str,
    intro: str = "",
    cta_label: str = "",
    cta_url: str = "",
    preheader: str = "",
    can_reply: bool = False,
) -> str:
    """Wrap content in the shared, email-client-safe HTML shell."""
    b = _brand()
    intro_block = paragraph(intro) if intro else ""

    cta_block = ""
    if cta_label and cta_url:
        safe_url = escape(cta_url)
        cta_block = f"""
          <table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 12px;">
            <tr><td bgcolor="{CTA}" style="border-radius:6px;background:{CTA};">
              <a href="{safe_url}" target="_blank"
                 style="display:inline-block;padding:12px 26px;font-size:15px;font-weight:600;
                        color:#ffffff;text-decoration:none;border-radius:6px;">{cta_label}</a>
            </td></tr>
          </table>
          <p style="margin:0;font-size:12px;color:{SUBTLE};line-height:1.5;">
            If the button doesn't work, copy this link into your browser:<br>
            <a href="{safe_url}" style="color:{NAVY};word-break:break-all;">{safe_url}</a>
          </p>"""

    preheader_block = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>'
        if preheader
        else ""
    )
    reply_note = "" if can_reply else " Please do not reply directly."
    name = escape(b["name"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta name="x-apple-disable-message-reformatting">
  <meta name="color-scheme" content="light">
  <title>{strip_tags(heading)}</title>
</head>
<body style="margin:0;padding:0;background:{CANVAS};font-family:{FONT};">
  {preheader_block}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#ffffff;border:1px solid {BORDER};border-radius:8px;overflow:hidden;">

        <!-- Header -->
        <tr>
          <td bgcolor="{NAVY}" style="background:{NAVY};border-bottom:3px solid {ORANGE};padding:18px 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="vertical-align:middle;">
                  <img src="{escape(b["logo"])}" width="{b["logo_w"]}" height="{b["logo_h"]}" alt="{name}"
                       style="display:block;border:0;outline:none;height:{b["logo_h"]}px;width:{b["logo_w"]}px;
                              color:#ffffff;font-size:18px;font-weight:700;font-family:{FONT};">
                </td>
                <td align="right" style="vertical-align:middle;padding-left:12px;font-size:12px;color:{ON_NAVY_SOFT};">{escape(b["label"])}</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <h1 style="margin:0 0 16px;font-size:20px;line-height:1.35;font-weight:700;color:{INK};">{heading}</h1>
            {intro_block}
            <div style="font-size:15px;line-height:1.6;color:{TEXT};">{body_html}</div>
            {cta_block}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 32px 26px;background:{SURFACE};border-top:1px solid {BORDER};">
            <p style="margin:0 0 6px;font-size:13px;color:{MUTED};font-weight:600;">{name}</p>
            {_footer_contact(b)}
            <p style="margin:0;font-size:11px;color:{SUBTLE};line-height:1.6;">
              © {b["year"]} {name}. This is an automated message.{reply_note}
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _to_text(markup: str) -> str:
    """Turns trusted markup into text. Escaped user text comes back as they typed it."""
    return html_lib.unescape(strip_tags(markup))


def _auto_text(
    heading: str, intro: str, body_html: str, cta_label: str = "", cta_url: str = ""
) -> str:
    """Generate a readable plain-text fallback from the HTML body."""
    text = re.sub(r"<\s*br\s*/?>", "\n", body_html, flags=re.I)
    text = re.sub(r"</\s*(p|div|tr|h[1-6]|li)\s*>", "\n", text, flags=re.I)
    text = re.sub(r"</\s*td\s*>", "  ", text, flags=re.I)
    text = _to_text(text.replace("&#10003;", "-")).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    parts = [_to_text(heading).strip()]
    if intro:
        parts.append(_to_text(intro).strip())
    parts.append(text)
    if cta_label and cta_url:
        parts.append(f"{_to_text(cta_label)}: {cta_url}")
    return "\n\n".join(part for part in parts if part)


@lru_cache(maxsize=1)
def _logo_bytes() -> bytes:
    return LOGO_FILE.read_bytes()


def _attach_logo(message: EmailMultiAlternatives) -> None:
    image = MIMEImage(_logo_bytes(), "png")
    image.add_header("Content-ID", f"<{LOGO_CID}>")
    image.add_header("Content-Disposition", "inline", filename="lesson-lab-logo.png")
    # "related" tells mail clients the image belongs to the HTML, not a download.
    message.mixed_subtype = "related"
    message.attach(image)


def html_for_preview(message: EmailMultiAlternatives) -> str:
    """The HTML with its attached logo built in, because a browser can't read cid: links."""
    logo = base64.b64encode(_logo_bytes()).decode("ascii")
    return message.alternatives[0][0].replace(f"cid:{LOGO_CID}", f"data:image/png;base64,{logo}")


def build_branded_email(
    *,
    subject: str,
    to,
    heading: str,
    body_html: str,
    intro: str = "",
    cta_label: str = "",
    cta_url: str = "",
    preheader: str = "",
    text_body: str | None = None,
    reply_to: str | None = None,
) -> EmailMultiAlternatives:
    """Builds the message without sending it, for send_branded_email() and the previews."""
    html = render_branded_email(
        heading=heading,
        body_html=body_html,
        intro=intro,
        cta_label=cta_label,
        cta_url=cta_url,
        preheader=preheader,
        can_reply=bool(reply_to),
    )
    if text_body is None:
        text_body = _auto_text(heading, intro, body_html, cta_label, cta_url)

    message = EmailMultiAlternatives(
        # Subjects can hold text from a public form, so line breaks are removed.
        subject=" ".join(subject.split()),
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to] if isinstance(to, str) else list(to),
        reply_to=[reply_to] if reply_to else None,
    )
    message.attach_alternative(html, "text/html")
    if not settings.BRAND_LOGO_URL:
        _attach_logo(message)
    return message


def send_branded_email(*, fail_silently: bool = False, **content) -> bool:
    """Sends a transactional email in the branded shell. Returns True on success.

    Call this from a Celery task, so that sending never blocks a web request. Failures
    raise by default, so the task shows as failed.
    """
    message = build_branded_email(**content)
    try:
        message.send(fail_silently=False)
    except Exception as exc:
        # Only the type: the message holds codes and links, which must never be logged.
        logger.error("branded_email_send_failed error_type=%s", type(exc).__name__)
        if not fail_silently:
            raise
        return False
    return True
