from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TenantModel


class School(models.Model):
    class Type(models.TextChoices):
        BOYS = "boys", "Boys"
        GIRLS = "girls", "Girls"
        MIXED = "mixed", "Mixed"

    class Stage(models.TextChoices):
        KINDERGARTEN = "kindergarten", "Kindergarten"
        PRIMARY = "primary", "Primary"
        INTERMEDIATE = "intermediate", "Intermediate"
        SECONDARY = "secondary", "Secondary"

    class Region(models.TextChoices):
        RIYADH = "riyadh", "Riyadh"
        MAKKAH = "makkah", "Makkah"
        MADINAH = "madinah", "Madinah"
        EASTERN = "eastern", "Eastern Province"
        QASSIM = "qassim", "Qassim"
        ASIR = "asir", "Asir"
        TABUK = "tabuk", "Tabuk"
        HAIL = "hail", "Hail"
        NORTHERN_BORDERS = "northern_borders", "Northern Borders"
        JAZAN = "jazan", "Jazan"
        NAJRAN = "najran", "Najran"
        AL_BAHAH = "al_bahah", "Al Bahah"
        AL_JAWF = "al_jawf", "Al Jawf"

    name_en = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200)
    code = models.SlugField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    # Onboarding details. Blank is allowed only for schools created before these
    # fields existed; the platform API requires them for every new school.
    school_type = models.CharField(max_length=20, choices=Type.choices, blank=True)
    education_stages = models.JSONField(default=list, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    region = models.CharField(max_length=30, choices=Region.choices, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=300, blank=True)
    cr_number = models.CharField("commercial registration number", max_length=20, blank=True)
    moe_license_number = models.CharField("MOE license number", max_length=20, blank=True)
    estimated_students = models.PositiveIntegerField(null=True, blank=True)
    admin_name = models.CharField(max_length=120, blank=True)
    admin_phone = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Blank is allowed many times, for schools created before emails were required.
            models.UniqueConstraint(
                Lower("email"), condition=~models.Q(email=""), name="unique_school_email"
            ),
        ]

    def __str__(self):
        return self.name_en


class Membership(TenantModel):
    class Role(models.TextChoices):
        SCHOOL_ADMIN = "SCHOOL_ADMIN", "School Admin"
        PRINCIPAL = "PRINCIPAL", "Principal"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"
        PARENT = "PARENT", "Parent"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "user"], name="unique_membership_per_school"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.school} ({self.role})"
