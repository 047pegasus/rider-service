# Generated manually for Dead Letter Queue model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0003_alter_delivery_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeadLetterQueue',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('topic', models.CharField(help_text='Kafka topic name', max_length=255)),
                ('event_data', models.JSONField(help_text='Original event data')),
                ('error_message', models.TextField(blank=True, help_text='Error that caused the failure', null=True)),
                ('retry_count', models.IntegerField(default=0, help_text='Number of retry attempts')),
                ('max_retries', models.IntegerField(default=5, help_text='Maximum number of retries')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('retrying', 'Retrying'), ('processed', 'Processed'), ('failed', 'Failed')], default='pending', max_length=50)),
                ('next_retry_at', models.DateTimeField(blank=True, help_text='When to retry next', null=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dead_letter_queue',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='deadletterqueue',
            index=models.Index(fields=['status'], name='dead_letter_status_idx'),
        ),
        migrations.AddIndex(
            model_name='deadletterqueue',
            index=models.Index(fields=['next_retry_at'], name='dead_letter_next_retry_idx'),
        ),
        migrations.AddIndex(
            model_name='deadletterqueue',
            index=models.Index(fields=['topic'], name='dead_letter_topic_idx'),
        ),
    ]
