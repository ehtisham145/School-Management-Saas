from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('browser_agent', '0001_initial'),
        ('tenancy', '0006_school_kind'),
    ]

    operations = [
        migrations.AlterField(
            model_name='browsertask',
            name='status',
            field=models.CharField(choices=[('queued', 'Queued'), ('running', 'Running'), ('awaiting_user', 'Waiting for the user'), ('done', 'Done'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('limit_reached', 'Limit reached')], default='queued', max_length=20),
        ),
        migrations.AddIndex(
            model_name='browsertask',
            index=models.Index(fields=['status', 'created_by'], name='browser_task_status_user'),
        ),
    ]
