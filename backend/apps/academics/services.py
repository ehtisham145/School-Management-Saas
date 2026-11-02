from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.academics.models import AcademicYear, Term


@transaction.atomic
def set_current_year(school, year_id):
    year = get_object_or_404(AcademicYear.objects.select_for_update(), school=school, id=year_id)
    AcademicYear.objects.filter(school=school, is_current=True).exclude(id=year.id).update(
        is_current=False
    )
    year.is_current = True
    year.save(update_fields=["is_current", "updated_at"])
    return year


def create_term(school, *, academic_year, name_en, name_ar, start_date, end_date):
    if academic_year.school_id != school.id:
        raise ValidationError({"academic_year": "Academic year not found."})
    if start_date < academic_year.start_date or end_date > academic_year.end_date:
        raise ValidationError({"start_date": "Term dates must be inside the academic year."})

    return Term.objects.create(
        school=school,
        academic_year=academic_year,
        name_en=name_en,
        name_ar=name_ar,
        start_date=start_date,
        end_date=end_date,
    )
