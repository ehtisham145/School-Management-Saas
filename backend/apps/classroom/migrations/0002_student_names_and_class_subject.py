from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Lower


def split_full_names(apps, schema_editor):
    Student = apps.get_model("classroom", "Student")
    students = list(Student.objects.only("id", "full_name"))
    for student in students:
        first, _, last = " ".join(student.full_name.split()).partition(" ")
        student.first_name = first[:100] or "-"
        student.last_name = last[:100]
    Student.objects.bulk_update(students, ["first_name", "last_name"], batch_size=500)


def join_full_names(apps, schema_editor):
    Student = apps.get_model("classroom", "Student")
    students = list(Student.objects.only("id", "first_name", "last_name"))
    for student in students:
        student.full_name = f"{student.first_name} {student.last_name}".strip()[:150]
    Student.objects.bulk_update(students, ["full_name"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("classroom", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="classroom",
            name="unique_classroom_name_per_workspace",
        ),
        migrations.AddConstraint(
            model_name="classroom",
            constraint=models.UniqueConstraint(
                models.F("school"),
                Lower("name"),
                Lower("subject"),
                name="unique_classroom_name_subject",
            ),
        ),
        migrations.RemoveIndex(
            model_name="student",
            name="student_roster_idx",
        ),
        migrations.AddField(
            model_name="student",
            name="first_name",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="student",
            name="last_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="student",
            name="father_name",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="student",
            name="student_number",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name="student",
            name="full_name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.RunPython(split_full_names, join_full_names),
        migrations.RemoveField(
            model_name="student",
            name="full_name",
        ),
        migrations.AlterModelOptions(
            name="student",
            options={"ordering": ["first_name", "last_name", "id"]},
        ),
        migrations.AddIndex(
            model_name="student",
            index=models.Index(
                fields=["school", "classroom", "first_name", "last_name"],
                name="student_roster_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="student",
            constraint=models.UniqueConstraint(
                condition=~Q(student_number=""),
                fields=("classroom", "student_number"),
                name="unique_student_number_per_class",
            ),
        ),
    ]
