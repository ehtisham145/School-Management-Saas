from celery import shared_task

from apps.integrations.email.adapter import send_school_admin_welcome_email


@shared_task(queue="emails")
def send_school_admin_welcome_email_task(to_email, school_name):
    send_school_admin_welcome_email(to_email, school_name)
