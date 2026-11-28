import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenancy', '0006_school_kind'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BrowserTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('goal', models.TextField(max_length=2000)),
                ('start_url', models.URLField(blank=True, max_length=2000)),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('done', 'Done'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('limit_reached', 'Limit reached')], default='queued', max_length=20)),
                ('answer', models.TextField(blank=True, max_length=10000)),
                ('failure_reason', models.CharField(blank=True, max_length=40)),
                ('steps_taken', models.PositiveIntegerField(default=0)),
                ('input_tokens', models.PositiveIntegerField(default=0)),
                ('output_tokens', models.PositiveIntegerField(default=0)),
                ('cost_usd', models.DecimalField(decimal_places=6, default=Decimal('0'), max_digits=10)),
                ('model', models.CharField(blank=True, max_length=50)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='browser_tasks', to=settings.AUTH_USER_MODEL)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.school')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='BrowserStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('number', models.PositiveIntegerField()),
                ('action', models.CharField(max_length=20)),
                ('domain', models.CharField(blank=True, max_length=253)),
                ('verdict', models.CharField(choices=[('ok', 'Done'), ('blocked', 'Blocked by policy'), ('failed', 'Failed on the page'), ('invalid', 'Invalid action from the AI')], max_length=10)),
                ('note', models.CharField(blank=True, max_length=60)),
                ('input_tokens', models.PositiveIntegerField(default=0)),
                ('output_tokens', models.PositiveIntegerField(default=0)),
                ('duration_ms', models.PositiveIntegerField(default=0)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tenancy.school')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='browser_agent.browsertask')),
            ],
            options={
                'ordering': ['task', 'number'],
                'constraints': [models.UniqueConstraint(fields=('task', 'number'), name='unique_browser_step_number')],
            },
        ),
    ]
