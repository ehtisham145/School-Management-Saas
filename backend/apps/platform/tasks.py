from celery import shared_task

from apps.integrations.email.adapter import (
    send_lead_notification_email,
    send_school_admin_welcome_email,
)


@shared_task(queue="emails")
def send_school_admin_welcome_email_task(to_email, school_name):
    send_school_admin_welcome_email(to_email, school_name)


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
