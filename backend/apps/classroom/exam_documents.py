"""The test paper and its answer key, in English or Arabic.

build_paper() works out every line once: numbering, letters, marks and labels. The PDF
(render_paper_pdf, here) and the Word file (apps/integrations/word/exam_document.py) only
lay those lines out, so the two never disagree.
"""

from decimal import Decimal
from itertools import groupby

from django.utils.html import escape

from apps.classroom import exams
from apps.integrations.pdf.renderer import html_to_pdf

LABELS = {
    "en": {
        "teacher": "Teacher",
        "subject": "Subject",
        "grade": "Grade",
        "class": "Class",
        "date": "Date",
        "time": "Time",
        "minutes": "{n} minutes",
        "total": "Total marks",
        "name": "Name",
        "number": "Roll number",
        "instructions": "Instructions",
        "answer_key": "Answer key",
        "answer": "Answer",
        "page": "Page {n}",
        "true": "True",
        "false": "False",
        "marks": "({n} marks)",
        "one_mark": "(1 mark)",
        "watermark": "Made with Lesson Lab",
        "letters": ("A", "B", "C", "D", "E", "F"),
        "kinds": {
            exams.MCQ: "Multiple choice",
            exams.TRUE_FALSE: "True or false",
            exams.FILL_BLANK: "Fill in the blanks",
            exams.SHORT_ANSWER: "Short answers",
        },
    },
    "ar": {
        "teacher": "المعلم",
        "subject": "المادة",
        "grade": "الصف",
        "class": "الفصل",
        "date": "التاريخ",
        "time": "الزمن",
        "minutes": "{n} دقيقة",
        "total": "الدرجة الكلية",
        "name": "الاسم",
        "number": "الرقم",
        "instructions": "التعليمات",
        "answer_key": "نموذج الإجابة",
        "answer": "الإجابة",
        "page": "صفحة {n}",
        "true": "صح",
        "false": "خطأ",
        "marks": "(الدرجة: {n})",
        "one_mark": "(الدرجة: 1)",
        "watermark": "أُعدّ باستخدام Lesson Lab",
        "letters": ("أ", "ب", "ج", "د", "هـ", "و"),
        "kinds": {
            exams.MCQ: "اختيار من متعدد",
            exams.TRUE_FALSE: "صح أو خطأ",
            exams.FILL_BLANK: "أكمل الفراغ",
            exams.SHORT_ANSWER: "أجب باختصار",
        },
    },
}
PRINTED_BLANK = "_" * 14
ANSWER_LINES = 3


def _marks(value, labels):
    shown = exams.format_marks(value)
    return labels["one_mark"] if shown == "1" else labels["marks"].format(n=shown)


def _answer_text(question, labels):
    if question.kind == exams.MCQ:
        index = question.correct_option
        if index is not None and index < len(question.options):
            return f"({labels['letters'][index]}) {question.options[index]}"
        return ""
    if question.kind == exams.TRUE_FALSE:
        return labels["true"] if question.answer == "true" else labels["false"]
    return question.answer


def _paper_question(question, number, labels, answers):
    item = {
        "number": number,
        "text": question.text.replace(exams.BLANK, PRINTED_BLANK),
        "marks": _marks(question.marks, labels),
        "options": [],
        "choices": "",
        "lines": 0,
        "answer": "",
        "explanation": "",
        "page": "",
    }
    if answers:
        item["answer"] = _answer_text(question, labels)
        item["explanation"] = question.explanation
        if question.source_page:
            item["page"] = labels["page"].format(n=question.source_page)
    elif question.kind == exams.MCQ:
        item["options"] = [
            f"({labels['letters'][index]}) {option}"
            for index, option in enumerate(question.options[: len(labels["letters"])])
        ]
    elif question.kind == exams.TRUE_FALSE:
        item["choices"] = f"(   ) {labels['true']}        (   ) {labels['false']}"
    elif question.kind == exams.SHORT_ANSWER:
        item["lines"] = ANSWER_LINES
    return item


def build_paper(exam, *, teacher_name, answers=False, watermark=False, theme=None):
    """Every line of the paper, or of its answer key, ready to lay out.

    `theme` is the workspace's paper design; without it, the test's own is used."""
    language = exam.language if exam.language in LABELS else "en"
    labels = LABELS[language]
    theme = {**exams.DEFAULT_THEME, **(theme if theme is not None else exam.theme or {})}
    colors = exams.THEMES.get(theme["color"], exams.THEMES["navy"])
    questions = list(exam.questions.all())
    total = sum((question.marks for question in questions), Decimal("0"))

    details = [
        (labels["subject"], exam.subject),
        (labels["grade"], exam.grade),
        (labels["class"], exam.classroom.name if exam.classroom else ""),
        (labels["date"], exam.exam_date.strftime("%d/%m/%Y") if exam.exam_date else ""),
        (
            labels["time"],
            labels["minutes"].format(n=exam.duration_minutes) if exam.duration_minutes else "",
        ),
        (labels["total"], exams.format_marks(total)),
        (labels["teacher"], teacher_name),
    ]

    sections = []
    number = 0
    for kind, group in groupby(questions, key=lambda question: question.kind):
        group = list(group)
        items = []
        for question in group:
            number += 1
            items.append(_paper_question(question, number, labels, answers))
        section_total = sum((question.marks for question in group), Decimal("0"))
        sections.append(
            {
                "heading": f"{labels['kinds'][kind]} {_marks(section_total, labels)}",
                "questions": items,
            }
        )

    return {
        "language": language,
        "rtl": language == "ar",
        "title": f"{labels['answer_key']}: {exam.title}" if answers else exam.title,
        "accent": colors["accent"],
        "soft": colors["soft"],
        "font_size": exams.FONT_SIZES.get(theme["font_size"], exams.FONT_SIZES["normal"]),
        # An answer key is read, not written on, so it stays in one column.
        "columns": 2 if theme.get("columns") == 2 and not answers else 1,
        "details": [(label, value) for label, value in details if value],
        "name_line": (
            [labels["name"], labels["number"]] if theme.get("name_line") and not answers else []
        ),
        "instructions": (
            (labels["instructions"], exam.instructions)
            if exam.instructions and not answers
            else None
        ),
        "answer_label": labels["answer"],
        "sections": sections,
        "footer": labels["watermark"] if watermark else "",
    }


def _css_text(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _styles(paper):
    size = paper["font_size"]
    accent, soft = paper["accent"], paper["soft"]
    footer = (
        f'@bottom-center {{ content: "{_css_text(paper["footer"])}"; font-size: 9px; '
        "color: #64748b; }"
        if paper["footer"]
        else ""
    )
    return f"""
@page {{ size: A4; margin: 16mm 15mm 18mm; {footer} }}
body {{ font-family: "IBM Plex Sans Arabic", "IBM Plex Sans", "DejaVu Sans", sans-serif;
       color: #0f172a; font-size: {size}px; line-height: 1.5; }}
h1 {{ color: {accent}; font-size: {round(size * 1.8)}px; margin: 0 0 8px;
      padding-bottom: 8px; border-bottom: 3px solid {accent}; }}
.details {{ border-collapse: collapse; margin-bottom: 6px; }}
.details td {{ padding: 2px 0; padding-inline-end: 18px; }}
.details b {{ color: {accent}; }}
.name-line {{ margin: 12px 0 4px; }}
.name-line span {{ display: inline-block; width: 44%; margin-inline-end: 4%;
                   border-bottom: 1px solid #94a3b8; padding: 14px 0 2px; }}
.instructions {{ background: {soft}; border-radius: 6px; padding: 8px 10px; margin: 10px 0; }}
.questions {{ column-count: {paper["columns"]}; column-gap: 9mm; }}
h2 {{ background: {soft}; color: {accent}; font-size: {round(size * 1.15)}px;
      padding: 5px 8px; margin: 14px 0 8px; border-inline-start: 4px solid {accent};
      break-after: avoid; }}
.q {{ break-inside: avoid; margin: 0 0 10px; }}
.q p {{ margin: 0; }}
.marks {{ color: #64748b; font-size: 0.9em; }}
.options {{ list-style: none; margin: 4px 0 0; padding-inline-start: 18px; }}
.choices {{ padding-inline-start: 18px; margin-top: 4px; }}
.line {{ border-bottom: 1px solid #cbd5e1; height: 24px; }}
.answer {{ color: {accent}; font-weight: bold; margin-top: 2px; }}
.why {{ color: #475569; font-size: 0.92em; }}
"""


def _question_html(item, paper):
    parts = [
        f"<p><b>{item['number']}.</b> {escape(item['text'])} "
        f'<span class="marks">{escape(item["marks"])}</span></p>'
    ]
    if item["options"]:
        options = "".join(f"<li>{escape(option)}</li>" for option in item["options"])
        parts.append(f'<ul class="options">{options}</ul>')
    if item["choices"]:
        parts.append(f'<p class="choices">{escape(item["choices"])}</p>')
    parts.extend('<div class="line"></div>' for _ in range(item["lines"]))
    if item["answer"]:
        parts.append(
            f'<p class="answer">{escape(paper["answer_label"])}: {escape(item["answer"])}</p>'
        )
    why = " · ".join(value for value in (item["explanation"], item["page"]) if value)
    if why:
        parts.append(f'<p class="why">{escape(why)}</p>')
    return f'<div class="q">{"".join(parts)}</div>'


def render_paper_pdf(paper):
    direction = "rtl" if paper["rtl"] else "ltr"
    cells = [
        f"<td><b>{escape(label)}:</b> {escape(str(value))}</td>"
        for label, value in paper["details"]
    ]
    # Three details to a row, so the header stays short.
    rows = "".join(
        f"<tr>{''.join(cells[start : start + 3])}</tr>" for start in range(0, len(cells), 3)
    )
    name_line = "".join(f"<span>{escape(label)}:</span>" for label in paper["name_line"])
    instructions = ""
    if paper["instructions"]:
        label, text = paper["instructions"]
        instructions = (
            f'<div class="instructions"><b>{escape(label)}:</b> '
            f"{escape(text).replace(chr(10), '<br>')}</div>"
        )
    sections = "".join(
        f"<h2>{escape(section['heading'])}</h2>"
        + "".join(_question_html(item, paper) for item in section["questions"])
        for section in paper["sections"]
    )

    html = f"""<!doctype html>
<html lang="{paper["language"]}" dir="{direction}"><head><meta charset="utf-8">
<style>{_styles(paper)}</style></head>
<body>
<h1>{escape(paper["title"])}</h1>
<table class="details">{rows}</table>
{f'<div class="name-line">{name_line}</div>' if name_line else ""}
{instructions}
<div class="questions">{sections}</div>
</body></html>"""
    return html_to_pdf(html)
