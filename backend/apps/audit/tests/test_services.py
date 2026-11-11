import pytest
from django.db import transaction
from django.test import RequestFactory, override_settings

from apps.audit.models import AuditEvent
from apps.audit.services import SYSTEM, Actor, actor_from_request, client_ip, record_event
from apps.tenancy.models import School


def _request(**meta):
    return RequestFactory().get("/", **meta)


def test_client_ip_uses_remote_addr_without_a_proxy():
    request = _request(REMOTE_ADDR="198.51.100.4", HTTP_X_FORWARDED_FOR="10.0.0.1")

    assert client_ip(request) == "198.51.100.4"


@override_settings(TRUST_X_FORWARDED_FOR=True)
def test_client_ip_reads_the_proxy_header_in_production():
    request = _request(REMOTE_ADDR="172.18.0.2", HTTP_X_FORWARDED_FOR="203.0.113.9, 172.18.0.2")

    assert client_ip(request) == "203.0.113.9"


@override_settings(TRUST_X_FORWARDED_FOR=True)
def test_client_ip_ignores_a_value_that_is_not_an_address():
    assert client_ip(_request(HTTP_X_FORWARDED_FOR="<script>")) is None


def test_actor_from_request_keeps_the_user(db, django_user_model):
    request = _request(REMOTE_ADDR="198.51.100.4")
    request.user = django_user_model.objects.create_user("owner")

    actor = actor_from_request(request)

    assert actor.user == request.user
    assert actor.ip_address == "198.51.100.4"


def test_record_event_keeps_a_label_after_the_user_is_deleted(db, django_user_model):
    user = django_user_model.objects.create_user("owner", email="owner@example.com")
    school = School.objects.create(name_en="A", name_ar="أ", code="a")

    record_event(Actor(user=user), AuditEvent.Action.SCHOOL_CREATED, school, school=school)
    user.delete()

    event = AuditEvent.objects.get()
    assert event.actor is None
    assert event.actor_label == "owner@example.com"
    assert event.target_label == "A"


def test_system_events_have_no_actor(db):
    school = School.objects.create(name_en="A", name_ar="أ", code="a")

    record_event(SYSTEM, AuditEvent.Action.SCHOOL_ACTIVATED, school)

    assert AuditEvent.objects.get().actor_label == ""


@pytest.mark.django_db(transaction=True)
def test_record_event_refuses_to_run_outside_a_transaction():
    school = School.objects.create(name_en="A", name_ar="أ", code="a")

    with pytest.raises(RuntimeError):
        record_event(SYSTEM, AuditEvent.Action.SCHOOL_ACTIVATED, school)

    with transaction.atomic():
        record_event(SYSTEM, AuditEvent.Action.SCHOOL_ACTIVATED, school)
    assert AuditEvent.objects.count() == 1
