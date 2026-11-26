"""Builds a Word file from a lesson plan. The only place that talks to python-docx."""

import re
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x0F, 0x1D, 0x31)
ORANGE = RGBColor(0xC2, 0x55, 0x0C)
INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x64, 0x74, 0x8B)
FONT = "Arial"
ARABIC_LETTER = re.compile(r"[؀-ۿ]")
# Word rejects a file whose XML elements are out of order, so new ones go before these.
AFTER_BIDI = (
    "w:adjustRightInd",
    "w:snapToGrid",
    "w:spacing",
    "w:ind",
    "w:contextualSpacing",
    "w:mirrorIndents",
    "w:suppressOverlap",
    "w:jc",
    "w:textDirection",
    "w:textAlignment",
    "w:textboxTightWrap",
    "w:outlineLvl",
    "w:divId",
    "w:cnfStyle",
    "w:rPr",
    "w:sectPr",
    "w:pPrChange",
)
AFTER_BORDER = (
    "w:shd",
    "w:tabs",
    "w:suppressAutoHyphens",
    "w:kinsoku",
    "w:wordWrap",
    "w:overflowPunct",
    "w:topLinePunct",
    "w:autoSpaceDE",
    "w:autoSpaceDN",
    "w:bidi",
    *AFTER_BIDI,
)

SECTIONS = ("objectives", "materials", "activities", "assessment", "homework")
TITLES = {
    "en": {
        "objectives": "Objectives",
        "materials": "Materials",
        "activities": "Activities",
        "assessment": "Assessment",
        "homework": "Homework",
        "subject": "Subject",
        "grade": "Grade",
        "classroom": "Class",
        "date": "Date",
        "teacher": "Teacher",
        "watermark": "Made with Lesson Lab",
        "brand": "Lesson Lab",
    },
    "ar": {
        "objectives": "الأهداف",
        "materials": "المواد",
        "activities": "الأنشطة",
        "assessment": "التقييم",
        "homework": "الواجب",
        "subject": "المادة",
        "grade": "الصف",
        "classroom": "الفصل",
        "date": "التاريخ",
        "teacher": "المعلم",
        "watermark": "أُعدّ باستخدام Lesson Lab",
        "brand": "Lesson Lab",
    },
}


def _set_rtl(paragraph, rtl):
    if not rtl:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        return
    # python-docx has no setting for right-to-left paragraphs, so it goes on the XML.
    # No alignment is set: a right-to-left paragraph starts at the right by itself.
    paragraph._p.get_or_add_pPr().insert_element_before(OxmlElement("w:bidi"), *AFTER_BIDI)


def _add_run(paragraph, text, *, size, color, bold=False, rtl=False):
    run = paragraph.add_run(text)
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    # Arabic text takes its font, size and weight from the "complex script" settings.
    run.font.cs_bold = bold
    run.font.rtl = rtl
    properties = run._r.get_or_add_rPr()
    properties.rFonts.set(qn("w:cs"), FONT)
    size_cs = OxmlElement("w:szCs")
    size_cs.set(qn("w:val"), str(size * 2))
    properties.sz.addnext(size_cs)
    return run


def _paragraph(document, text, *, size, color, bold=False, rtl=False, style=None, after=6):
    paragraph = document.add_paragraph(style=style)
    _set_rtl(paragraph, rtl)
    paragraph.paragraph_format.space_after = Pt(after)
    _add_run(paragraph, text, size=size, color=color, bold=bold, rtl=rtl)
    return paragraph


def _bottom_border(paragraph):
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in {
        "w:val": "single",
        "w:sz": "12",
        "w:space": "6",
        "w:color": "F5781E",
    }.items():
        bottom.set(qn(key), value)
    borders.append(bottom)
    paragraph._p.get_or_add_pPr().insert_element_before(borders, *AFTER_BORDER)


def build_lesson_document(plan, *, watermark=False):
    """`plan` holds the title, subject, grade, class name, date, teacher and the five text
    sections."""
    # The teacher's name says nothing about the lesson's language, so it isn't counted.
    sample = " ".join(str(value) for key, value in plan.items() if value and key != "teacher")
    language = "ar" if ARABIC_LETTER.search(sample) else "en"
    rtl = language == "ar"
    titles = TITLES[language]

    document = Document()
    for section in document.sections:
        section.top_margin = section.bottom_margin = Cm(2)
        section.left_margin = section.right_margin = Cm(2.2)

    title = _paragraph(document, plan["title"], size=24, color=NAVY, bold=True, rtl=rtl, after=4)
    details = [
        f"{titles[key]}: {plan[key]}"
        for key in ("subject", "grade", "classroom", "date", "teacher")
        if plan.get(key)
    ]
    if details:
        title = _paragraph(document, "   |   ".join(details), size=11, color=ORANGE, rtl=rtl)
    _bottom_border(title)

    for key in SECTIONS:
        points = [line.strip() for line in (plan.get(key) or "").splitlines() if line.strip()]
        if not points:
            continue
        heading = _paragraph(document, titles[key], size=15, color=NAVY, bold=True, rtl=rtl)
        heading.paragraph_format.space_before = Pt(14)
        heading.paragraph_format.keep_with_next = True
        for point in points:
            _paragraph(document, point, size=12, color=INK, rtl=rtl, style="List Bullet", after=3)

    # Every file carries the brand; the trial's says it was made with Lesson Lab.
    footer = document.sections[0].footer.paragraphs[0]
    _set_rtl(footer, rtl)
    _add_run(footer, titles["watermark" if watermark else "brand"], size=9, color=MUTED, rtl=rtl)

    output = BytesIO()
    document.save(output)
    return output.getvalue()
