"""What a workspace may do, from its current subscription."""

from dataclasses import dataclass
from datetime import date

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
    ai_per_month: int
    pro_features: bool


TRIAL_LIMITS = Limits(
    classes=2,
    students=30,
    lesson_plans=10,
    presentation_exports=3,
    ai_per_month=0,
    pro_features=False,
)
TEACHER_LIMITS = Limits(
    classes=5,
    students=100,
    lesson_plans=None,
    presentation_exports=None,
    ai_per_month=0,
    pro_features=False,
)
TEACHER_PRO_LIMITS = Limits(
    classes=None,
    students=None,
    lesson_plans=None,
    presentation_exports=None,
    ai_per_month=50,
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
