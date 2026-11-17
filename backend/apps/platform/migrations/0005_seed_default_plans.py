from decimal import Decimal

from django.db import migrations


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("platform", "Plan")
    plans = [
        {
            "code": "basic",
            "name_en": "Basic",
            "name_ar": "أساسي",
        },
        {
            "code": "premium",
            "name_en": "Premium",
            "name_ar": "مميز",
        },
        {
            "code": "custom",
            "name_en": "Custom",
            "name_ar": "مخصص",
        },
        {
            "code": "teacher",
            "name_en": "Teacher",
            "name_ar": "معلم",
        },
        {
            "code": "teacher_pro",
            "name_en": "Teacher Pro",
            "name_ar": "معلم برو",
        },
    ]
    for data in plans:
        Plan.objects.get_or_create(
            code=data["code"],
            defaults={
                **data,
                "monthly_price": Decimal("0.00"),
                "yearly_price": Decimal("0.00"),
                "max_students": None,
                "is_active": False,
            },
        )


def remove_plans(apps, schema_editor):
    Plan = apps.get_model("platform", "Plan")
    Plan.objects.filter(
        code__in=["basic", "premium", "custom", "teacher", "teacher_pro"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0004_demo_request_plan_choices"),
    ]

    operations = [
        migrations.RunPython(seed_plans, remove_plans),
    ]
