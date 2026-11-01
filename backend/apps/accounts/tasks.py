from celery import shared_task

from apps.integrations.email.adapter import send_otp_email


@shared_task(queue="emails")
def send_otp_email_task(to_email, code):
    send_otp_email(to_email, code)
