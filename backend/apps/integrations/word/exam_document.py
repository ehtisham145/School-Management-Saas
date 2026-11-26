"""Lays out a test paper, or its answer key, as a Word file. Talks to python-docx only.

The lines come ready from apps/classroom/exam_documents.build_paper(), so this file and
the PDF always show the same numbers, letters and marks.
"""

from io import BytesIO

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from apps.integrations.word.lesson_document import (
    AFTER_BORDER,
    INK,
    MUTED,
    _add_run,
    _paragraph,
    _set_rtl,
)

LINE_COLOR = "CBD5E1"
COLUMN_GAP_TWIPS = "510"  # 9 mm


def _rule(paragraph, color_hex, *, size="12"):
    """A line under the paragraph, such as under the title or as a line to write on."""
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    settings = {"w:val": "single", "w:sz": size, "w:space": "4", "w:color": color_hex}
    for key, value in settings.items():
        bottom.set(qn(key), value)
    borders.append(bottom)
    paragraph._p.get_or_add_pPr().insert_element_before(borders, *AFTER_BORDER)


def _two_columns(section):
    columns = section._sectPr.find(qn("w:cols"))
    if columns is None:
        columns = OxmlElement("w:cols")
        section._sectPr.append(columns)
    columns.set(qn("w:num"), "2")
    columns.set(qn("w:space"), COLUMN_GAP_TWIPS)


def build_exam_document(paper):
    rtl = paper["rtl"]
    accent_hex = paper["accent"].lstrip("#").upper()
    accent = RGBColor.from_string(accent_hex)
    size = paper["font_size"]

    document = Document()
    for section in document.sections:
        section.top_margin = section.bottom_margin = Cm(1.8)
        section.left_margin = section.right_margin = Cm(1.8)

    title = _paragraph(
        document, paper["title"], size=round(size * 1.8), color=accent, bold=True, rtl=rtl
    )
    _rule(title, accent_hex, size="18")
    if paper["details"]:
        _paragraph(
            document,
            "   |   ".join(f"{label}: {value}" for label, value in paper["details"]),
            size=size - 1,
            color=INK,
            rtl=rtl,
        )
    if paper["name_line"]:
        _paragraph(
            document,
            "      ".join(f"{label}: ____________________" for label in paper["name_line"]),
            size=size,
            color=INK,
            rtl=rtl,
            after=8,
        )
    if paper["instructions"]:
        label, text = paper["instructions"]
        _paragraph(document, f"{label}: {text}", size=size, color=INK, rtl=rtl, after=8)

    if paper["columns"] == 2:
        # A new section on the same page, so only the questions sit in two columns.
        _two_columns(document.add_section(WD_SECTION_START.CONTINUOUS))

    for block in paper["sections"]:
        heading = _paragraph(
            document, block["heading"], size=round(size * 1.15), color=accent, bold=True, rtl=rtl
        )
        heading.paragraph_format.space_before = Pt(10)
        heading.paragraph_format.keep_with_next = True
        for item in block["questions"]:
            _question(document, item, paper, size=size, accent=accent, rtl=rtl)

    if paper["footer"]:
        footer = document.sections[0].footer.paragraphs[0]
        _set_rtl(footer, rtl)
        _add_run(footer, paper["footer"], size=9, color=MUTED, rtl=rtl)

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _question(document, item, paper, *, size, accent, rtl):
    text = document.add_paragraph()
    _set_rtl(text, rtl)
    text.paragraph_format.space_after = Pt(2)
    text.paragraph_format.keep_with_next = bool(
        item["options"] or item["choices"] or item["lines"] or item["answer"]
    )
    _add_run(text, f"{item['number']}. ", size=size, color=INK, bold=True, rtl=rtl)
    _add_run(text, f"{item['text']} ", size=size, color=INK, rtl=rtl)
    _add_run(text, item["marks"], size=size - 1, color=MUTED, rtl=rtl)

    last = text
    indent = Cm(0.6)
    for option in item["options"]:
        last = _paragraph(document, option, size=size, color=INK, rtl=rtl, after=1)
        # Indent from the side the text starts on.
        if rtl:
            last.paragraph_format.right_indent = indent
        else:
            last.paragraph_format.left_indent = indent
    if item["choices"]:
        last = _paragraph(document, item["choices"], size=size, color=INK, rtl=rtl, after=2)
    for _ in range(item["lines"]):
        last = _paragraph(document, " ", size=size, color=INK, rtl=rtl, after=0)
        _rule(last, LINE_COLOR, size="6")
    if item["answer"]:
        last = _paragraph(
            document,
            f"{paper['answer_label']}: {item['answer']}",
            size=size,
            color=accent,
            bold=True,
            rtl=rtl,
            after=1,
        )
    why = " · ".join(value for value in (item["explanation"], item["page"]) if value)
    if why:
        last = _paragraph(document, why, size=size - 1, color=MUTED, rtl=rtl, after=2)
    # Space between questions.
    last.paragraph_format.space_after = Pt(8)
