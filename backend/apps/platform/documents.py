"""The quotation document: what goes in the PDF, in English or Arabic.

Backend text isn't translated through Django i18n yet (docs/roadmap.md), so the two
languages of this one document are kept here, side by side.
"""

from decimal import Decimal

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from hijridate import Gregorian

from apps.integrations.pdf.renderer import html_to_pdf

LABELS = {
    "en": {
        "title": "Quotation",
        "number": "Quotation no.",
        "date": "Date",
        "valid_until": "Valid until",
        "prepared_for": "Prepared for",
        "plan": "Plan",
        "billing": "Billing",
        "monthly": "Monthly",
        "yearly": "Yearly",
        "description": "Description",
        "quantity": "Qty",
        "unit_price": "Unit price",
        "amount": "Amount",
        "subtotal": "Subtotal",
        "vat": "VAT ({rate}%)",
        "total": "Total",
        "notes": "Notes",
        "vat_number": "VAT number",
        "currency": "SAR",
        "prices_note": "All prices are in Saudi riyals.",
        "hijri_suffix": "AH",
    },
    "ar": {
        "title": "عرض سعر",
        "number": "رقم العرض",
        "date": "التاريخ",
        "valid_until": "صالح حتى",
        "prepared_for": "مقدم إلى",
        "plan": "الباقة",
        "billing": "الفوترة",
        "monthly": "شهري",
        "yearly": "سنوي",
        "description": "الوصف",
        "quantity": "الكمية",
        "unit_price": "سعر الوحدة",
        "amount": "المبلغ",
        "subtotal": "المجموع الفرعي",
        "vat": "ضريبة القيمة المضافة ({rate}٪)",
        "total": "الإجمالي",
        "notes": "ملاحظات",
        "vat_number": "الرقم الضريبي",
        "currency": "ر.س",
        "prices_note": "جميع الأسعار بالريال السعودي.",
        "hijri_suffix": "هـ",
    },
}


def format_money(value: Decimal) -> str:
    return f"{value:,.2f}"


def format_rate(value: Decimal) -> str:
    """15.00 -> 15, 7.50 -> 7.5"""
    return f"{value.normalize():f}"


def hijri_date(day) -> str:
    """Umm al-Qura date for display (ADR-0005). Blank outside the calendar's range."""
    try:
        hijri = Gregorian.fromdate(day).to_hijri()
    except (OverflowError, ValueError):
        return ""
    return f"{hijri.day:02d}/{hijri.month:02d}/{hijri.year}"


def quotation_context(quotation):
    language = quotation.language
    labels = LABELS[language]
    issued_on = timezone.localdate(quotation.sent_at) if quotation.sent_at else timezone.localdate()
    plan_name = ""
    if quotation.plan is not None:
        plan_name = quotation.plan.name_ar if language == "ar" else quotation.plan.name_en

    return {
        "language": language,
        "direction": "rtl" if language == "ar" else "ltr",
        "labels": labels,
        "vat_label": labels["vat"].format(rate=format_rate(quotation.vat_rate)),
        "quotation": quotation,
        "issued_on": issued_on,
        "issued_on_hijri": hijri_date(issued_on),
        "valid_until_hijri": hijri_date(quotation.valid_until),
        "plan_name": plan_name,
        "billing_label": labels.get(quotation.billing_cycle, ""),
        "items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": format_money(item.unit_price),
                "amount": format_money(item.amount),
            }
            for item in quotation.items.all()
        ],
        "subtotal": format_money(quotation.subtotal),
        "vat_amount": format_money(quotation.vat_amount),
        "total": format_money(quotation.total),
        "company": {
            "name": settings.COMPANY_NAME,
            "address": settings.COMPANY_ADDRESS,
            "website": settings.COMPANY_WEBSITE,
            "email": settings.SUPPORT_EMAIL,
            "vat_number": settings.COMPANY_VAT_NUMBER,
        },
    }


def render_quotation_html(quotation) -> str:
    return render_to_string("pdf/quotation.html", quotation_context(quotation))


def render_quotation_pdf(quotation) -> bytes:
    return html_to_pdf(render_quotation_html(quotation))


def quotation_filename(quotation) -> str:
    return f"{quotation.number}.pdf"
