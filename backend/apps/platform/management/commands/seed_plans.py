from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.platform.models import Plan

PLANS = [
    {"code": "basic", "name_en": "Basic", "name_ar": "أساسي"},
    {"code": "premium", "name_en": "Premium", "name_ar": "مميز"},
    {"code": "custom", "name_en": "Custom", "name_ar": "مخصص"},
    {"code": "teacher", "name_en": "Teacher", "name_ar": "معلم"},
    {"code": "teacher_pro", "name_en": "Teacher Pro", "name_ar": "معلم برو"},
]


class Command(BaseCommand):
    help = "Creates the starter plans (price 0, inactive) if they don't exist yet."

    def handle(self, *args, **options):
        for data in PLANS:
            _, created = Plan.objects.get_or_create(
                code=data["code"],
                defaults={
                    **data,
                    "monthly_price": Decimal("0.00"),
                    "yearly_price": Decimal("0.00"),
                    "max_students": None,
                    "is_active": False,
                },
            )
            label = "created" if created else "already exists"
            self.stdout.write(f"{data['code']}: {label}")
