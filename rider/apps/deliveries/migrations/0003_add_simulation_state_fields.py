# Generated migration - Add simulation state fields to Delivery model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0002_add_dead_letter_queue'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='current_route_index',
            field=models.IntegerField(default=0, help_text='Current position in route for simulation'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='simulation_status',
            field=models.CharField(default='idle', help_text='Simulation status: idle, going_to_pickup, at_pickup, going_to_delivery, completed', max_length=50),
        ),
        migrations.AddField(
            model_name='delivery',
            name='last_location_lat',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='delivery',
            name='last_location_lng',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True),
        ),
    ]
