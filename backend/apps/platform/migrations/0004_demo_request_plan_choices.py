from django.db import migrations, models


def advanced_to_custom(apps, schema_editor):
    """The Advanced plan became the Custom plan; keep old requests readable."""
    demo_requests = apps.get_model("platform", "DemoRequest")
    demo_requests.objects.filter(plan="advanced").update(plan="custom")


def custom_to_advanced(apps, schema_editor):
    demo_requests = apps.get_model("platform", "DemoRequest")
    demo_requests.objects.filter(plan="custom").update(plan="advanced")


class Migration(migrations.Migration):
    dependencies = [
        ("platform", "0003_billing"),
    ]

    operations = [
        migrations.AlterField(
            model_name="demorequest",
            name="plan",
            field=models.CharField(
                blank=True,
                choices=[
                    ("basic", "Basic"),
                    ("premium", "Premium"),
                    ("custom", "Custom"),
                    ("teacher", "Teacher"),
                    ("teacher_pro", "Teacher Pro"),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(advanced_to_custom, custom_to_advanced),
    ]
