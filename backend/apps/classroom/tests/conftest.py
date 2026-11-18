from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.platform.models import BillingCycle, Plan, Subscription
from apps.tenancy.models import Membership, School


class Workspace:
    def __init__(self, name):
        self.school = School.objects.create(
            name_en=name, code=f"teacher-{name.lower()}", kind=School.Kind.INDIVIDUAL
        )
        self.user = User.objects.create_user(
            username=f"{name.lower()}@example.com",
            email=f"{name.lower()}@example.com",
            password="correct-pass123",
            first_name=name,
        )
        self.membership = Membership.objects.create(
            school=self.school, user=self.user, role=Membership.Role.TEACHER
        )
        self.client = APIClient()
        self.client.force_login(self.user, backend="django.contrib.auth.backends.ModelBackend")
        session = self.client.session
        session["active_membership_id"] = self.membership.id
        session.save()

    def subscribe(self, code="teacher", *, is_trial=False, days=30):
        plan, _ = Plan.objects.get_or_create(
            code=code,
            defaults={"name_en": code, "name_ar": code, "monthly_price": 49, "yearly_price": 588},
        )
        today = timezone.localdate()
        return Subscription.objects.create(
            school=self.school,
            plan=plan,
            billing_cycle=BillingCycle.MONTHLY,
            price=0 if is_trial else plan.monthly_price,
            starts_on=today - timedelta(days=1),
            ends_on=today + timedelta(days=days),
            is_trial=is_trial,
        )


@pytest.fixture
def trial(db):
    workspace = Workspace("Sara")
    workspace.subscribe(is_trial=True, days=7)
    return workspace


@pytest.fixture
def teacher(db):
    workspace = Workspace("Tariq")
    workspace.subscribe("teacher")
    return workspace


@pytest.fixture
def pro(db):
    workspace = Workspace("Noor")
    workspace.subscribe("teacher_pro")
    return workspace


@pytest.fixture
def expired(db):
    workspace = Workspace("Omar")
    subscription = workspace.subscribe(is_trial=True, days=7)
    Subscription.objects.filter(pk=subscription.pk).update(
        starts_on=timezone.localdate() - timedelta(days=8),
        ends_on=timezone.localdate() - timedelta(days=1),
    )
    return workspace


@pytest.fixture
def other(db):
    workspace = Workspace("Layla")
    workspace.subscribe("teacher_pro")
    return workspace
