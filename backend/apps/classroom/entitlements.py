"""What a workspace may do, from its current subscription."""

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.utils import timezone

from apps.platform.selectors import get_current_subscription

TEACHER_PRO_CODE = "teacher_pro"


@dataclass(frozen=True)
class Limits:
    """None means no limit."""

    classes: int | None
    students: int | None
    lesson_plans: int | None
    presentation_exports: int | None
    ai_lessons: int
    ai_exams: int
    # "trial": counted over the whole trial. "month": counted again each calendar month.
    # Both AI lesson plans and AI tests follow it.
    ai_period: str
    pro_features: bool


TRIAL_LIMITS = Limits(
    classes=2,
    students=30,
    lesson_plans=20,
    presentation_exports=10,
    ai_lessons=10,
    ai_exams=5,
    ai_period="trial",
    pro_features=False,
)
TEACHER_LIMITS = Limits(
    classes=5,
    students=100,
    lesson_plans=None,
    presentation_exports=None,
    ai_lessons=30,
    ai_exams=20,
    ai_period="month",
    pro_features=False,
)
TEACHER_PRO_LIMITS = Limits(
    classes=None,
    students=None,
    lesson_plans=None,
    presentation_exports=None,
    ai_lessons=100,
    ai_exams=60,
    ai_period="month",
    pro_features=True,
)


@dataclass(frozen=True)
class WorkspaceAccess:
    tier: str
    read_only: bool
    limits: Limits
    ends_on: date | None
    days_left: int | None

    @property
    def is_trial(self):
        return self.tier == "trial"

    @property
    def classes_enabled(self):
        """Classes, students and everything built on them: attendance, marks, report
        cards and parent messages. Part of the school plan, not the teacher's (ADR-0027)."""
        return settings.TEACHER_CLASSES_ENABLED

    @property
    def ai_since(self):
        """From when AI lesson plans and tests are counted. None counts every one ever made."""
        if self.limits.ai_period == "month":
            return timezone.localdate().replace(day=1)
        return None


def get_workspace_access(school):
    today = timezone.localdate()
    subscription = get_current_subscription(school, today)
    if subscription is None:
        # Nothing is lost when a plan ends: the teacher can still read and export.
        return WorkspaceAccess("expired", True, TRIAL_LIMITS, None, None)

    days_left = (subscription.ends_on - today).days
    if subscription.is_trial:
        tier, limits = "trial", TRIAL_LIMITS
    elif subscription.plan.code == TEACHER_PRO_CODE:
        tier, limits = TEACHER_PRO_CODE, TEACHER_PRO_LIMITS
    else:
        tier, limits = "teacher", TEACHER_LIMITS
    return WorkspaceAccess(tier, False, limits, subscription.ends_on, days_left)
