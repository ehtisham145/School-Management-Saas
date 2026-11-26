"""Builds a PowerPoint file from a lesson plan. The only place that talks to python-pptx."""

import re
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

NAVY = RGBColor(0x0F, 0x1D, 0x31)
ORANGE = RGBColor(0xF5, 0x78, 0x1E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x64, 0x74, 0x8B)

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)
MARGIN = Inches(0.8)
MAX_POINTS_PER_SLIDE = 7
ARABIC_LETTER = re.compile(r"[؀-ۿ]")

SECTION_TITLES = {
    "en": {
        "objectives": "Objectives",
        "materials": "Materials",
        "activities": "Activities",
        "assessment": "Assessment",
        "homework": "Homework",
        "continued": "continued",
        "watermark": "Made with Lesson Lab",
        "brand": "Lesson Lab",
        "prepared": "Prepared by {name}",
    },
    "ar": {
        "objectives": "الأهداف",
        "materials": "المواد",
        "activities": "الأنشطة",
        "assessment": "التقييم",
        "homework": "الواجب",
        "continued": "تابع",
        "watermark": "أُعدّ باستخدام Lesson Lab",
        "brand": "Lesson Lab",
        "prepared": "إعداد: {name}",
    },
}


def _write(frame, text, *, size, color, bold=False, rtl=False, first=True):
    paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
    paragraph.alignment = PP_ALIGN.RIGHT if rtl else PP_ALIGN.LEFT
    # python-pptx has no setting for right-to-left text, so it goes on the XML.
    paragraph._p.get_or_add_pPr().set("rtl", "1" if rtl else "0")
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return paragraph


def _text_box(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    box.text_frame.word_wrap = True
    return box.text_frame


def _footer(slide, text, rtl, *, number=None):
    """The brand, or the trial's mark, along the bottom, and the slide number."""
    width = SLIDE_WIDTH - MARGIN * 2
    frame = _text_box(slide, MARGIN, SLIDE_HEIGHT - Inches(0.6), width, Inches(0.4))
    _write(frame, text, size=11, color=MUTED, rtl=rtl)
    if number is not None:
        # The number sits on the side the text ends on.
        frame = _text_box(slide, MARGIN, SLIDE_HEIGHT - Inches(0.6), width, Inches(0.4))
        paragraph = _write(frame, str(number), size=11, color=MUTED, rtl=rtl)
        paragraph.alignment = PP_ALIGN.LEFT if rtl else PP_ALIGN.RIGHT


def _title_slide(deck, plan, rtl, footer, prepared):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    background.fill.solid()
    background.fill.fore_color.rgb = NAVY
    background.line.fill.background()

    brand = _text_box(slide, MARGIN, Inches(0.6), SLIDE_WIDTH - MARGIN * 2, Inches(0.6))
    _write(brand, "Lesson Lab", size=20, color=ORANGE, bold=True, rtl=rtl)

    frame = _text_box(slide, MARGIN, Inches(2.3), SLIDE_WIDTH - MARGIN * 2, Inches(2.2))
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    _write(frame, plan["title"], size=44, color=WHITE, bold=True, rtl=rtl)

    details = " · ".join(value for value in (plan.get("subject"), plan.get("grade")) if value)
    if details:
        _write(frame, details, size=22, color=ORANGE, rtl=rtl, first=False)
    if prepared:
        _write(frame, prepared, size=18, color=WHITE, rtl=rtl, first=False)
    _footer(slide, footer, rtl)


def _content_slide(deck, title, points, rtl, footer, number):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, Inches(0.16))
    accent.fill.solid()
    accent.fill.fore_color.rgb = ORANGE
    accent.line.fill.background()

    heading = _text_box(slide, MARGIN, Inches(0.5), SLIDE_WIDTH - MARGIN * 2, Inches(1))
    _write(heading, title, size=34, color=NAVY, bold=True, rtl=rtl)

    body = _text_box(slide, MARGIN, Inches(1.6), SLIDE_WIDTH - MARGIN * 2, Inches(5))
    for index, point in enumerate(points):
        paragraph = _write(body, f"•  {point}", size=22, color=INK, rtl=rtl, first=index == 0)
        paragraph.space_after = Pt(10)
    _footer(slide, footer, rtl, number=number)


def build_lesson_deck(plan, *, watermark=False, teacher_name=""):
    """`plan` holds the title, subject, grade and the five text sections.

    Every slide carries the Lesson Lab brand; a trial's says it was made with Lesson Lab.
    The title slide names the teacher who prepared it."""
    sample = " ".join(str(value) for value in plan.values())
    language = "ar" if ARABIC_LETTER.search(sample) else "en"
    rtl = language == "ar"
    titles = SECTION_TITLES[language]
    brand = titles["watermark"] if watermark else titles["brand"]
    footer = f"{brand} · {teacher_name}" if teacher_name else brand
    prepared = titles["prepared"].format(name=teacher_name) if teacher_name else ""

    deck = Presentation()
    deck.slide_width = SLIDE_WIDTH
    deck.slide_height = SLIDE_HEIGHT
    _title_slide(deck, plan, rtl, brand, prepared)

    for section in ("objectives", "materials", "activities", "assessment", "homework"):
        points = [line.strip() for line in (plan.get(section) or "").splitlines() if line.strip()]
        for page, start in enumerate(range(0, len(points), MAX_POINTS_PER_SLIDE)):
            title = titles[section]
            if page:
                title = f"{title} ({titles['continued']})"
            number = len(deck.slides) + 1
            _content_slide(
                deck, title, points[start : start + MAX_POINTS_PER_SLIDE], rtl, footer, number
            )

    output = BytesIO()
    deck.save(output)
    return output.getvalue()
