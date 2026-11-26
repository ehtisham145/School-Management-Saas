import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from apps.classroom.models import ParentMessage, Student
from apps.integrations.email.adapter import send_parent_message_email

logger = logging.getLogger(__name__)


@shared_task(queue="ai", soft_time_limit=240, time_limit=300)
def generate_exam_draft_task(school_id, draft_id):
    # Imported here: the services module imports this one.
    from apps.classroom.services import fail_exam_draft, write_exam_draft

    try:
        write_exam_draft(school_id, draft_id)
    except SoftTimeLimitExceeded:
        fail_exam_draft(school_id, draft_id, "timed_out")
    except Exception:
        # The teacher sees a failed draft instead of waiting for one that never comes.
        logger.exception("exam_draft_crashed", extra={"draft": draft_id})
        fail_exam_draft(school_id, draft_id, "service_unavailable")


@shared_task
def clean_up_exam_drafts_task():
    from apps.classroom.services import clean_up_exam_drafts

    clean_up_exam_drafts()


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
