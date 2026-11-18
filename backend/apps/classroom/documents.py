"""The student report card PDF, in English or Arabic."""

from django.utils import timezone
from django.utils.html import escape

from apps.integrations.pdf.renderer import html_to_pdf

LABELS = {
    "en": {
        "title": "Report card",
        "student": "Student",
        "class": "Class",
        "teacher": "Teacher",
        "issued": "Issued",
        "results": "Results",
        "assessment": "Assessment",
        "date": "Date",
        "mark": "Mark",
        "percent": "Percent",
        "overall": "Overall",
        "attendance": "Attendance",
        "present": "Present",
        "absent": "Absent",
        "late": "Late",
        "excused": "Excused",
        "empty": "No results yet.",
    },
    "ar": {
        "title": "شهادة الطالب",
        "student": "الطالب",
        "class": "الفصل",
        "teacher": "المعلم",
        "issued": "تاريخ الإصدار",
        "results": "النتائج",
        "assessment": "التقييم",
        "date": "التاريخ",
        "mark": "الدرجة",
        "percent": "النسبة",
        "overall": "الإجمالي",
        "attendance": "الحضور",
        "present": "حاضر",
        "absent": "غائب",
        "late": "متأخر",
        "excused": "بعذر",
        "empty": "لا توجد نتائج بعد.",
    },
}

STYLES = """
@page { size: A4; margin: 18mm; }
body { font-family: "IBM Plex Sans Arabic", "IBM Plex Sans", "DejaVu Sans", sans-serif;
       color: #0f172a; font-size: 12px; }
h1 { color: #0f1d31; font-size: 24px; margin: 0 0 14px; border-bottom: 3px solid #f5781e;
     padding-bottom: 10px; }
h2 { color: #0f1d31; font-size: 15px; margin: 22px 0 8px; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #e2e8f0; padding: 7px 9px; text-align: start; }
th { background: #f8fafc; }
.details td { border: 0; padding: 3px 0; }
.overall td { font-weight: bold; background: #fef0e5; }
"""


def _percent(value, maximum):
    return f"{value / maximum * 100:.0f}%"


def render_report_card_pdf(*, student, teacher_name, report, language):
    labels = LABELS[language]
    direction = "rtl" if language == "ar" else "ltr"

    rows = ""
    earned = total = 0
    for mark in report["marks"]:
        assessment = mark.assessment
        earned += mark.value
        total += assessment.max_marks
        rows += (
            f"<tr><td>{escape(assessment.title)}</td><td>{assessment.date.isoformat()}</td>"
            f"<td>{mark.value} / {assessment.max_marks}</td>"
            f"<td>{_percent(mark.value, assessment.max_marks)}</td></tr>"
        )

    if rows:
        rows += (
            f'<tr class="overall"><td colspan="2">{labels["overall"]}</td>'
            f"<td>{earned} / {total}</td><td>{_percent(earned, total)}</td></tr>"
        )
        results = (
            f"<table><thead><tr><th>{labels['assessment']}</th><th>{labels['date']}</th>"
            f"<th>{labels['mark']}</th><th>{labels['percent']}</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    else:
        results = f"<p>{labels['empty']}</p>"

    statuses = ("present", "absent", "late", "excused")
    head = "".join(f"<th>{labels[status]}</th>" for status in statuses)
    cells = "".join(f"<td>{report['attendance'].get(status, 0)}</td>" for status in statuses)

    html = f"""<!doctype html>
<html lang="{language}" dir="{direction}"><head><meta charset="utf-8"><style>{STYLES}</style></head>
<body>
<h1>{labels["title"]}</h1>
<table class="details">
<tr><td>{labels["student"]}: <b>{escape(student.full_name)}</b></td>
<td>{labels["class"]}: <b>{escape(student.classroom.name)}</b></td></tr>
<tr><td>{labels["teacher"]}: <b>{escape(teacher_name)}</b></td>
<td>{labels["issued"]}: <b>{timezone.localdate().isoformat()}</b></td></tr>
</table>
<h2>{labels["results"]}</h2>{results}
<h2>{labels["attendance"]}</h2>
<table><thead><tr>{head}</tr></thead><tbody><tr>{cells}</tr></tbody></table>
</body></html>"""
    return html_to_pdf(html)
