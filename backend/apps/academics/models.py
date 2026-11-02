from django.db import models
from django.db.models import F, Q

from apps.core.models import TenantModel


class AcademicYear(TenantModel):
    name = models.CharField(max_length=20)  # e.g. "2026-2027"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["school", "name"], name="unique_year_name_per_school"),
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(is_current=True),
                name="one_current_year_per_school",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="year_end_after_start",
            ),
        ]

    def __str__(self):
        return self.name


class Term(TenantModel):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="terms")
    name_en = models.CharField(max_length=50)
    name_ar = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "name_en"], name="unique_term_name_per_year"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="term_end_after_start",
            ),
        ]

    def __str__(self):
        return self.name_en
