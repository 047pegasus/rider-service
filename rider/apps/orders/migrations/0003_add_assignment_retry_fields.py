# Generated manually for assignment retry fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_add_denial_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='assignment_retry_count',
            field=models.IntegerField(default=0, help_text='Number of times assignment was retried'),
        ),
        migrations.AddField(
            model_name='order',
            name='last_assignment_retry_at',
            field=models.DateTimeField(blank=True, help_text='Last time assignment was retried', null=True),
        ),
    ]
