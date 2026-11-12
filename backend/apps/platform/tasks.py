from celery import shared_task

from apps.integrations.email.adapter import (
    send_lead_notification_email,
    send_quotation_email,
    send_school_admin_welcome_email,
)


@shared_task(queue="emails")
def send_school_admin_welcome_email_task(to_email, school_name, username=None):
    send_school_admin_welcome_email(to_email, school_name, username)


@shared_task(queue="emails")
def send_lead_notification_email_task(*, subject, heading, intro, rows, message, reply_to):
    send_lead_notification_email(
        subject=subject,
        heading=heading,
        intro=intro,
        rows=rows,
        message=message,
        reply_to=reply_to,
    )


@shared_task(queue="emails")
def send_quotation_email_task(quotation_id):
    """Builds the PDF and emails it. Takes an id and reloads, so it is safe to retry."""
    # Imported here: services import this module to queue the task.
    from apps.platform.documents import quotation_filename, render_quotation_pdf
    from apps.platform.selectors import get_quotation

    quotation = get_quotation(quotation_id)
    if quotation is None or quotation.status != quotation.Status.SENT:
        return

    send_quotation_email(
        to_email=quotation.recipient_email,
        recipient_name=quotation.recipient_name,
        organization=quotation.recipient_organization,
        number=quotation.number,
        total=f"{quotation.total:,.2f}",
        valid_until=quotation.valid_until.strftime("%d/%m/%Y"),
        attachment=(
            quotation_filename(quotation),
            render_quotation_pdf(quotation),
            "application/pdf",
        ),
    )


@shared_task
def expire_overdue_subscriptions_task():
    """Daily (CELERY_BEAT_SCHEDULE). Returns how many subscriptions it expired."""
    from apps.platform.services import expire_overdue_subscriptions

    return expire_overdue_subscriptions()
