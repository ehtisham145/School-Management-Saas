from django.core import mail

from apps.accounts.tasks import send_otp_email_task


def test_send_otp_email_task_sends_email():
    send_otp_email_task.delay("parent@example.com", "123456")

    assert len(mail.outbox) == 1
    assert "123456" in mail.outbox[0].body
    assert mail.outbox[0].to == ["parent@example.com"]
