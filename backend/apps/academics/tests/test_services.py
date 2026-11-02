from datetime import date

import pytest
from django.http import Http404
from rest_framework.exceptions import ValidationError

from apps.academics.models import AcademicYear
from apps.academics.services import create_term, set_current_year


def _year(school, name="2026-2027", is_current=False):
    return AcademicYear.objects.create(
        school=school,
        name=name,
        start_date=date(2026, 8, 1),
        end_date=date(2027, 6, 30),
        is_current=is_current,
    )


def _create_term(school, year, start=date(2026, 8, 1), end=date(2026, 12, 31)):
    return create_term(
        school,
        academic_year=year,
        name_en="Term 1",
        name_ar="الفصل الأول",
        start_date=start,
        end_date=end,
    )


def test_set_current_year_switches_the_current_year(two_schools):
    school_a, _ = two_schools
    old = _year(school_a, name="2025-2026", is_current=True)
    new = _year(school_a, name="2026-2027")

    set_current_year(school_a, new.id)

    old.refresh_from_db()
    new.refresh_from_db()
    assert not old.is_current
    assert new.is_current


def test_set_current_year_rejects_another_schools_year(two_schools):
    school_a, school_b = two_schools
    year_b = _year(school_b)

    with pytest.raises(Http404):
        set_current_year(school_a, year_b.id)

    year_b.refresh_from_db()
    assert not year_b.is_current


def test_create_term_inside_year(two_schools):
    school_a, _ = two_schools
    year = _year(school_a)

    term = _create_term(school_a, year)

    assert term.school == school_a
    assert term.academic_year == year


def test_create_term_rejects_dates_outside_year(two_schools):
    school_a, _ = two_schools
    year = _year(school_a)

    with pytest.raises(ValidationError):
        _create_term(school_a, year, start=date(2026, 7, 1), end=date(2026, 12, 31))


def test_create_term_rejects_another_schools_year(two_schools):
    school_a, school_b = two_schools
    year_b = _year(school_b)

    with pytest.raises(ValidationError):
        _create_term(school_a, year_b)
