import django.db.models.deletion
import django.db.models.functions.text
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("classroom", "0002_student_names_and_class_subject"),
        ("tenancy", "0006_school_kind"),
    ]

    operations = [
        migrations.AddField(
            model_name="aigeneration",
            name="kind",
            field=models.CharField(
                choices=[("lesson", "Lesson plan"), ("exam", "Test")],
                default="lesson",
                max_length=10,
            ),
        ),
        migrations.AddIndex(
            model_name="aigeneration",
            index=models.Index(
                fields=["school", "kind", "created_at"], name="ai_generation_kind_idx"
            ),
        ),
        migrations.CreateModel(
            name="SourceDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sha256", models.CharField(max_length=64)),
                ("filename", models.CharField(max_length=255)),
                ("page_count", models.PositiveSmallIntegerField()),
                ("pages", models.JSONField(default=list)),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tenancy.school")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("school", "sha256"), name="one_source_per_file"),
                ],
                "indexes": [models.Index(fields=["updated_at"], name="source_document_age_idx")],
            },
        ),
        migrations.CreateModel(
            name="ExamPattern",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                ("sections", models.JSONField()),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tenancy.school")),
            ],
            options={
                "ordering": ["name", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        models.F("school"),
                        django.db.models.functions.text.Lower("name"),
                        name="unique_exam_pattern_name",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ExamDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Being written"), ("ready", "Ready to review"), ("failed", "Failed")],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("settings", models.JSONField()),
                ("questions", models.JSONField(default=list)),
                ("requested", models.PositiveSmallIntegerField()),
                ("error", models.CharField(blank=True, max_length=40)),
                ("regenerations", models.PositiveSmallIntegerField(default=0)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drafts",
                        to="classroom.sourcedocument",
                    ),
                ),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tenancy.school")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["school", "status", "created_at"], name="exam_draft_status_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Exam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=200)),
                ("subject", models.CharField(blank=True, max_length=100)),
                ("grade", models.CharField(blank=True, max_length=50)),
                (
                    "language",
                    models.CharField(choices=[("en", "English"), ("ar", "Arabic")], default="en", max_length=2),
                ),
                ("exam_date", models.DateField(blank=True, null=True)),
                ("duration_minutes", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("instructions", models.TextField(blank=True, max_length=1000)),
                ("theme", models.JSONField(default=dict)),
                (
                    "source",
                    models.CharField(
                        choices=[("manual", "Written by the teacher"), ("ai", "Generated with AI")],
                        default="manual",
                        max_length=10,
                    ),
                ),
                (
                    "classroom",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exams",
                        to="classroom.classroom",
                    ),
                ),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tenancy.school")),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
                "indexes": [models.Index(fields=["school", "-updated_at"], name="exam_recent_idx")],
            },
        ),
        migrations.CreateModel(
            name="ExamQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("position", models.PositiveSmallIntegerField()),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("mcq", "Multiple choice"),
                            ("true_false", "True or false"),
                            ("fill_blank", "Fill in the blank"),
                            ("short_answer", "Short answer"),
                        ],
                        max_length=20,
                    ),
                ),
                ("text", models.TextField(max_length=1000)),
                ("options", models.JSONField(blank=True, default=list)),
                ("correct_option", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("answer", models.TextField(blank=True, max_length=1000)),
                ("explanation", models.TextField(blank=True, max_length=1000)),
                ("marks", models.DecimalField(decimal_places=2, max_digits=5)),
                (
                    "difficulty",
                    models.CharField(
                        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
                        default="medium",
                        max_length=10,
                    ),
                ),
                ("source_page", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "exam",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="classroom.exam",
                    ),
                ),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="tenancy.school")),
            ],
            options={
                "ordering": ["position", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("exam", "position"), name="one_question_per_position"),
                    models.CheckConstraint(
                        condition=models.Q(("marks__gt", Decimal("0"))),
                        name="exam_question_marks_positive",
                    ),
                ],
            },
        ),
    ]
