import pytest
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.services import Actor
from apps.platform.models import DemoRequest
from apps.platform.services import create_school_with_admin
from apps.tenancy.models import Membership, School

SCHOOLS_URL = "/api/platform/schools/"
SUMMARY_URL = f"{SCHOOLS_URL}summary/"
VALID_SCHOOL = {
    "name_en": "Al Noor School",
    "name_ar": "مدرسة النور",
    "code": "alnoor",
    "admin_email": "head@alnoor.example",
    "admin_name": "Sara Ahmed Ali",
    "admin_phone": "050 123 4567",
    "school_type": "girls",
    "education_stages": ["intermediate", "primary"],
    "email": "office@alnoor.example",
    "phone": "011 234 5678",
    "region": "riyadh",
    "city": "Riyadh",
    "address": "King Fahd Road",
    "cr_number": "1010123456",
    "moe_license_number": "778899",
    "estimated_students": 450,
}


def _status_url(school, action):
    return f"{SCHOOLS_URL}{school.id}/{action}/"


def _create(client, **overrides):
    return client.post(SCHOOLS_URL, {**VALID_SCHOOL, **overrides}, format="json")


# --- Creating a school


def test_create_saves_every_onboarding_field(platform_client):
    response = _create(platform_client)

    assert response.status_code == 201
    school = School.objects.get(code="alnoor")
    assert school.school_type == "girls"
    assert school.education_stages == ["primary", "intermediate"]
    assert school.email == "office@alnoor.example"
    assert school.phone == "+966112345678"
    assert school.region == "riyadh"
    assert school.city == "Riyadh"
    assert school.address == "King Fahd Road"
    assert school.cr_number == "1010123456"
    assert school.moe_license_number == "778899"
    assert school.estimated_students == 450
    assert school.admin_name == "Sara Ahmed Ali"
    assert school.admin_phone == "+966501234567"
    assert response.data["school_admin_email"] == "head@alnoor.example"


def test_create_names_a_new_admin_account(platform_client):
    _create(platform_client)

    admin = User.objects.get(email=VALID_SCHOOL["admin_email"])
    assert admin.first_name == "Sara"
    assert admin.last_name == "Ahmed Ali"
    assert admin.get_full_name() == "Sara Ahmed Ali"


OPTIONAL_FIELDS = ("code", "phone", "cr_number", "moe_license_number")


@pytest.mark.parametrize("field", [key for key in VALID_SCHOOL if key not in OPTIONAL_FIELDS])
def test_every_onboarding_field_is_required(platform_client, field):
    body = {key: value for key, value in VALID_SCHOOL.items() if key != field}

    response = platform_client.post(SCHOOLS_URL, body, format="json")

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not School.objects.filter(code="alnoor").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name_en", "مدرسة النور"),
        ("name_en", "1234"),
        ("name_ar", "Al Noor"),
        ("school_type", "other"),
        ("education_stages", []),
        ("education_stages", ["university"]),
        ("email", "not-an-email"),
        ("phone", "abc"),
        ("phone", "0212345678"),
        ("phone", "+923001234567"),
        ("region", "dubai"),
        ("city", ""),
        ("address", ""),
        ("address", "x" * 301),
        ("cr_number", "AB_12"),
        ("cr_number", "12$34"),
        ("cr_number", "---"),
        ("cr_number", "1" * 21),
        ("moe_license_number", "AB#12"),
        ("moe_license_number", "//"),
        ("moe_license_number", "1" * 21),
        ("estimated_students", 0),
        ("estimated_students", -5),
        ("estimated_students", 100_001),
        ("estimated_students", "many"),
        ("estimated_students", None),
        ("admin_name", ""),
        ("admin_phone", "0112345678"),
        ("admin_phone", "abc"),
    ],
)
def test_create_rejects_invalid_fields(platform_client, field, value):
    response = _create(platform_client, **{field: value})

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not School.objects.filter(code="alnoor").exists()
    assert not User.objects.filter(email=VALID_SCHOOL["admin_email"]).exists()


@pytest.mark.parametrize(
    ("field", "typed", "saved"),
    [
        ("cr_number", "١٠١٠١٢٣٤٥٦", "1010123456"),
        ("moe_license_number", "٧٧٨", "778"),
        ("cr_number", "CR-10101234", "CR-10101234"),
        ("cr_number", "10101234ab", "10101234ab"),
        ("cr_number", "123", "123"),
        ("moe_license_number", "AB-12/34", "AB-12/34"),
        ("moe_license_number", "رخصة ٧٧", "رخصة 77"),
        ("phone", "٠١١٢٣٤٥٦٧٨", "+966112345678"),
        ("phone", "0501234567", "+966501234567"),
        ("admin_phone", "+966501234567", "+966501234567"),
    ],
)
def test_create_accepts_arabic_digits_and_saves_them_the_same_way(
    platform_client, field, typed, saved
):
    assert _create(platform_client, **{field: typed}).status_code == 201

    assert getattr(School.objects.get(code="alnoor"), field) == saved


@pytest.mark.parametrize("field", ["phone", "cr_number", "moe_license_number"])
def test_create_works_without_the_optional_fields(platform_client, field):
    body = {key: value for key, value in VALID_SCHOOL.items() if key != field}

    assert platform_client.post(SCHOOLS_URL, body, format="json").status_code == 201

    assert getattr(School.objects.get(code="alnoor"), field) == ""


@pytest.mark.parametrize("field", ["phone", "cr_number", "moe_license_number"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_create_accepts_blank_optional_fields(platform_client, field, blank):
    assert _create(platform_client, **{field: blank}).status_code == 201

    assert getattr(School.objects.get(code="alnoor"), field) == ""


# --- Emails can be registered only once


@pytest.fixture
def existing_school(platform_client):
    assert _create(platform_client).status_code == 201


@pytest.mark.parametrize(
    "used",
    [
        "office@alnoor.example",
        "OFFICE@ALNOOR.EXAMPLE",
        "head@alnoor.example",
        "Head@Alnoor.Example",
    ],
)
@pytest.mark.parametrize("field", ["email", "admin_email"])
def test_a_registered_email_cannot_be_used_again(platform_client, existing_school, field, used):
    other = {"code": "second", "email": "second@example.com", "admin_email": "b@example.com"}

    response = _create(platform_client, **{**other, field: used})

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not School.objects.filter(code="second").exists()
    assert not User.objects.filter(username="second.admin").exists()


@pytest.mark.parametrize("field", ["email", "admin_email"])
def test_the_super_admins_email_cannot_be_used(platform_client, field):
    User.objects.filter(username="platform").update(email="owner@lessonlab.example")

    response = _create(platform_client, **{field: "OWNER@lessonlab.example"})

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]
    assert not School.objects.filter(code="alnoor").exists()
    assert not Membership.objects.filter(user__username="platform").exists()


@pytest.mark.parametrize("field", ["email", "admin_email"])
def test_any_other_users_email_cannot_be_used(platform_client, field):
    User.objects.create_user("teacher", email="teacher@example.com")

    response = _create(platform_client, **{field: "teacher@example.com"})

    assert response.status_code == 400
    assert field in response.data["error"]["fields"]


def test_school_and_admin_cannot_share_one_email(platform_client):
    response = _create(platform_client, admin_email="OFFICE@alnoor.example")

    assert response.status_code == 400
    assert "admin_email" in response.data["error"]["fields"]
    assert not School.objects.filter(code="alnoor").exists()


def test_new_emails_are_accepted_next_to_an_existing_school(platform_client, existing_school):
    response = _create(
        platform_client, code="second", email="second@example.com", admin_email="b@example.com"
    )

    assert response.status_code == 201


def test_older_schools_with_a_blank_email_do_not_clash(platform_client):
    School.objects.create(name_en="Old 1", name_ar="قديمة", code="old-1")
    School.objects.create(name_en="Old 2", name_ar="قديمة", code="old-2")

    assert _create(platform_client).status_code == 201


def test_the_database_refuses_a_school_email_in_any_letter_case(db):
    School.objects.create(name_en="A", name_ar="أ", code="a", email="same@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        School.objects.create(name_en="B", name_ar="ب", code="b", email="SAME@example.com")


@pytest.mark.parametrize(
    ("clash", "field"),
    [
        ({"email": "taken@example.com"}, "email"),
        ({"admin_email": "taken-admin@example.com"}, "admin_email"),
        ({"code": "taken"}, "code"),
    ],
)
def test_a_clash_that_slips_past_validation_is_still_a_field_error(db, clash, field):
    """Two requests at the same moment both pass validation, and the database stops one."""
    actor = User.objects.create_user("actor", is_platform_admin=True)
    School.objects.create(name_en="T", name_ar="ت", code="taken", email="taken@example.com")
    User.objects.create_user("holder", email="taken-admin@example.com")
    details = {
        key: value for key, value in VALID_SCHOOL.items() if key not in ("phone", "admin_phone")
    }

    with pytest.raises(ValidationError) as error:
        create_school_with_admin(actor=Actor(user=actor), **{**details, **clash})

    assert field in error.value.detail
    assert not School.objects.filter(code="alnoor").exists()


# --- Creating a school from a demo request


def test_create_from_demo_request_converts_it(platform_client):
    demo = DemoRequest.objects.create(name="Sara", school_name="Al Noor", email="s@example.com")

    response = _create(platform_client, demo_request=demo.id)

    assert response.status_code == 201
    assert "demo_request" not in response.data
    demo.refresh_from_db()
    assert demo.status == DemoRequest.Status.CONVERTED
    assert demo.converted_school.code == "alnoor"
    assert demo.is_handled is True


def test_create_from_unknown_demo_request_saves_nothing(platform_client):
    response = _create(platform_client, demo_request=999)

    assert response.status_code == 400
    assert "demo_request" in response.data["error"]["fields"]
    assert not School.objects.filter(code="alnoor").exists()


def test_a_demo_request_cannot_be_converted_twice(platform_client):
    demo = DemoRequest.objects.create(name="Sara", school_name="Al Noor", email="s@example.com")
    assert _create(platform_client, demo_request=demo.id).status_code == 201

    response = _create(
        platform_client,
        demo_request=demo.id,
        code="second",
        email="second@example.com",
        admin_email="b@example.com",
    )

    assert response.status_code == 400
    assert "demo_request" in response.data["error"]["fields"]
    assert not School.objects.filter(code="second").exists()


def test_failed_create_leaves_the_demo_request_unconverted(platform_client):
    User.objects.create_user("alnoor.admin")
    demo = DemoRequest.objects.create(name="Sara", school_name="Al Noor", email="s@example.com")

    assert _create(platform_client, demo_request=demo.id).status_code == 400

    demo.refresh_from_db()
    assert demo.status == DemoRequest.Status.NEW
    assert demo.converted_school is None


# --- Listing, filtering and counting


def test_list_filters_by_status(platform_client, two_schools):
    school_a, school_b = two_schools
    School.objects.filter(pk=school_b.pk).update(is_active=False)

    active = platform_client.get(f"{SCHOOLS_URL}?status=active")
    inactive = platform_client.get(f"{SCHOOLS_URL}?status=inactive")

    assert [row["id"] for row in active.data["results"]] == [school_a.id]
    assert [row["id"] for row in inactive.data["results"]] == [school_b.id]


def test_list_rejects_an_unknown_status(platform_client):
    response = platform_client.get(f"{SCHOOLS_URL}?status=deleted")

    assert response.status_code == 400
    assert "status" in response.data["error"]["fields"]


@pytest.mark.parametrize("term", ["noor", "مدرسة النور", "ALN", "jedd"])
def test_list_searches_names_code_and_city(platform_client, two_schools, term):
    match = School.objects.create(
        name_en="Al Noor", name_ar="مدرسة النور", code="aln-1", city="Jeddah"
    )

    response = platform_client.get(SCHOOLS_URL, {"search": term})

    assert [row["id"] for row in response.data["results"]] == [match.id]


def test_list_shows_the_first_school_admin_and_leaves_older_schools_blank(
    platform_client, two_schools
):
    school_a, school_b = two_schools
    first = User.objects.create_user("first", email="first@example.com")
    second = User.objects.create_user("second", email="second@example.com")
    teacher = User.objects.create_user("teacher", email="teacher@example.com")
    Membership.objects.create(school=school_a, user=teacher, role=Membership.Role.TEACHER)
    Membership.objects.create(school=school_a, user=first, role=Membership.Role.SCHOOL_ADMIN)
    Membership.objects.create(school=school_a, user=second, role=Membership.Role.SCHOOL_ADMIN)

    rows = {row["id"]: row for row in platform_client.get(SCHOOLS_URL).data["results"]}

    assert rows[school_a.id]["school_admin_email"] == "first@example.com"
    assert rows[school_a.id]["member_count"] == 3
    assert rows[school_b.id]["school_admin_email"] is None
    assert rows[school_b.id]["city"] == ""
    assert rows[school_b.id]["education_stages"] == []
    assert rows[school_b.id]["estimated_students"] is None


def test_list_query_count_does_not_grow_with_schools(
    platform_client, django_assert_max_num_queries
):
    School.objects.bulk_create(
        School(name_en=f"S{i}", name_ar=f"S{i}", code=f"s{i}") for i in range(20)
    )

    # Session, user, page count and page rows.
    with django_assert_max_num_queries(5):
        assert platform_client.get(SCHOOLS_URL).status_code == 200


def test_summary_counts_active_and_inactive_schools(platform_client, two_schools):
    School.objects.filter(pk=two_schools[1].pk).update(is_active=False)

    response = platform_client.get(SUMMARY_URL)

    assert response.status_code == 200
    assert response.data == {"total": 2, "active": 1, "inactive": 1}


def test_summary_is_zero_without_schools(platform_client):
    assert platform_client.get(SUMMARY_URL).data == {"total": 0, "active": 0, "inactive": 0}


# --- Activating and deactivating


def test_deactivate_and_activate_change_only_that_school(platform_client, two_schools):
    school_a, school_b = two_schools

    response = platform_client.post(_status_url(school_a, "deactivate"))

    assert response.status_code == 200
    assert response.data["is_active"] is False
    assert "member_count" in response.data
    school_a.refresh_from_db()
    school_b.refresh_from_db()
    assert school_a.is_active is False
    assert school_b.is_active is True

    response = platform_client.post(_status_url(school_a, "activate"))

    assert response.data["is_active"] is True
    school_a.refresh_from_db()
    assert school_a.is_active is True


@pytest.mark.parametrize(("action", "initial"), [("deactivate", False), ("activate", True)])
def test_repeating_a_status_change_is_harmless(platform_client, two_schools, action, initial):
    school = two_schools[0]
    School.objects.filter(pk=school.pk).update(is_active=initial)

    response = platform_client.post(_status_url(school, action))

    assert response.status_code == 200
    assert response.data["is_active"] is initial


@pytest.mark.parametrize("action", ["activate", "deactivate"])
def test_status_change_on_a_missing_school_is_404(platform_client, action):
    assert platform_client.post(f"{SCHOOLS_URL}999/{action}/").status_code == 404
    assert platform_client.post(f"{SCHOOLS_URL}abc/{action}/").status_code == 404


@pytest.mark.parametrize("action", ["activate", "deactivate"])
def test_status_change_needs_post(platform_client, two_schools, action):
    assert platform_client.get(_status_url(two_schools[0], action)).status_code == 405


# --- Who may call these endpoints


@pytest.mark.parametrize("action", ["activate", "deactivate"])
def test_status_change_is_denied_to_everyone_else(two_schools, school_admin_client, action):
    school_b = two_schools[1]
    School.objects.filter(pk=school_b.pk).update(is_active=action == "deactivate")

    for client in (APIClient(), school_admin_client):
        assert client.post(_status_url(school_b, action)).status_code == 403

    school_b.refresh_from_db()
    assert school_b.is_active is (action == "deactivate")


def test_summary_is_denied_to_everyone_else(two_schools, school_admin_client):
    for client in (APIClient(), school_admin_client):
        assert client.get(SUMMARY_URL).status_code == 403


def test_a_school_admin_cannot_read_another_school_through_the_filters(school_admin_client):
    assert school_admin_client.get(f"{SCHOOLS_URL}?search=school-b").status_code == 403
