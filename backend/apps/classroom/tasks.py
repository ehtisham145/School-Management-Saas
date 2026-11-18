from celery import shared_task

from apps.classroom.models import ParentMessage, Student
from apps.integrations.email.adapter import send_parent_message_email


@shared_task(queue="emails")
def send_parent_message_task(school_id, message_id):
    message = (
        ParentMessage.objects.filter(school_id=school_id, id=message_id)
        .select_related("classroom", "school")
        .first()
    )
    if message is None:
        return

    recipients = (
        Student.objects.filter(school_id=school_id, classroom_id=message.classroom_id)
        .exclude(parent_email="")
        .order_by()
        .values_list("parent_email", flat=True)
        .distinct()
    )
    for email in recipients:
        send_parent_message_email(
            to_email=email,
            teacher_name=message.school.name_en,
            class_name=message.classroom.name,
            subject=message.subject,
            body=message.body,
        )
