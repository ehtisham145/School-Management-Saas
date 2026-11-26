import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("classroom", "0003_ai_tests_from_pdf"),
        ("tenancy", "0006_school_kind"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaperDesign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("theme", models.JSONField(default=dict)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tenancy.school")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("school",), name="one_paper_design_per_workspace"),
                ],
            },
        ),
    ]
