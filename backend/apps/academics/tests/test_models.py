from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.academics.models import AcademicYear, Term


def _year(school, name="2026-2027", is_current=False, start=None, end=None):
    return AcademicYear.objects.create(
        school=school,
        name=name,
        start_date=start or date(2026, 8, 1),
        end_date=end or date(2027, 6, 30),
        is_current=is_current,
    )


def _term(year, name_en="Term 1", start=None, end=None):
    return Term.objects.create(
        school=year.school,
        academic_year=year,
        name_en=name_en,
        name_ar="الفصل الأول",
        start_date=start or date(2026, 8, 1),
        end_date=end or date(2026, 12, 31),
    )


def test_school_cannot_have_two_current_years(two_schools):
    school_a, _ = two_schools
    _year(school_a, name="2026-2027", is_current=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        _year(school_a, name="2027-2028", is_current=True)


def test_each_school_can_have_its_own_current_year(two_schools):
    school_a, school_b = two_schools

    _year(school_a, is_current=True)
    _year(school_b, is_current=True)

    assert AcademicYear.objects.filter(is_current=True).count() == 2


def test_school_can_have_many_non_current_years(two_schools):
    school_a, _ = two_schools

    _year(school_a, name="2025-2026")
    _year(school_a, name="2026-2027")

    assert AcademicYear.objects.filter(school=school_a).count() == 2


def test_year_name_is_unique_per_school(two_schools):
    school_a, _ = two_schools
    _year(school_a)

    with pytest.raises(IntegrityError), transaction.atomic():
        _year(school_a)


def test_same_year_name_is_allowed_in_another_school(two_schools):
    school_a, school_b = two_schools

    _year(school_a)
    _year(school_b)

    assert AcademicYear.objects.filter(name="2026-2027").count() == 2


def test_year_must_end_after_it_starts(two_schools):
    school_a, _ = two_schools

    with pytest.raises(IntegrityError), transaction.atomic():
        _year(school_a, start=date(2027, 6, 30), end=date(2026, 8, 1))


def test_term_name_is_unique_per_year(two_schools):
    school_a, _ = two_schools
    year = _year(school_a)
    _term(year)

    with pytest.raises(IntegrityError), transaction.atomic():
        _term(year)


def test_term_must_end_after_it_starts(two_schools):
    school_a, _ = two_schools
    year = _year(school_a)

    with pytest.raises(IntegrityError), transaction.atomic():
        _term(year, start=date(2026, 12, 31), end=date(2026, 8, 1))
