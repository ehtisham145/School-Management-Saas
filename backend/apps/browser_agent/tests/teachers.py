"""A signed-in individual teacher for the browser agent tests."""

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.browser_agent.models import AgentConsent
from apps.browser_agent.services import CONSENT_VERSION
from apps.platform.models import BillingCycle, Plan, Subscription
from apps.tenancy.models import Membership, School


class Teacher:
    def __init__(
        self, name, *, subscribed=True, kind=School.Kind.INDIVIDUAL, trial=False, consented=True
    ):
        self.school = School.objects.create(name_en=name, code=f"teacher-{name.lower()}", kind=kind)
        self.user = User.objects.create_user(
            username=f"{name.lower()}@example.com",
            email=f"{name.lower()}@example.com",
            password="correct-pass123",
            first_name=name,
            last_name="Ahmed",
        )
        self.membership = Membership.objects.create(
            school=self.school, user=self.user, role=Membership.Role.TEACHER
        )
        if subscribed:
            self.subscribe(trial=trial)
        if consented:
            AgentConsent.objects.create(school=self.school, user=self.user, version=CONSENT_VERSION)
        self.client = APIClient()
        self.client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")
        session = self.client.session
        session["active_membership_id"] = self.membership.id
        session.save()

    @property
    def session_key(self):
        return self.client.cookies["sessionid"].value

    def subscribe(self, *, trial=False, code="teacher"):
        plan, _ = Plan.objects.get_or_create(
            code=code,
            defaults={"name_en": code, "name_ar": code, "monthly_price": 49, "yearly_price": 588},
        )
        today = timezone.localdate()
        Subscription.objects.create(
            school=self.school,
            plan=plan,
            billing_cycle=BillingCycle.MONTHLY,
            price=0 if trial else plan.monthly_price,
            starts_on=today - timedelta(days=1),
            ends_on=today + timedelta(days=7 if trial else 30),
            is_trial=trial,
        )
