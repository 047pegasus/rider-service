# Generated migration - Add denial_count to Order model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='denial_count',
            field=models.IntegerField(default=0, help_text='Number of times delivery was denied by riders'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_completed',
            field=models.BooleanField(default=False, help_text='Whether payment has been completed'),
        ),
    ]
