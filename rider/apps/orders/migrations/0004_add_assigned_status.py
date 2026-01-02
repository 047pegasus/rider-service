# Generated migration - Add 'assigned' status to Order model
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_add_assignment_retry_fields'),
    ]

    operations = [
        # Note: This migration doesn't change the database schema,
        # it just adds a new choice to the existing CharField.
        # The status field already supports any string value,
        # so we just need to ensure the code handles 'assigned' status.
        # If you need to validate existing data, you can add a data migration here.
    ]
