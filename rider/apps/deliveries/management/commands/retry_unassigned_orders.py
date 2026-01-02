"""
Management command to retry assignment for unassigned orders.
This should be run periodically (e.g., every 5 minutes) via cron or celery.
"""
from django.core.management.base import BaseCommand
from apps.deliveries.services import delivery_service


class Command(BaseCommand):
    help = 'Retry assignment for orders that are ready but not yet assigned to a rider'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-retries',
            type=int,
            default=10,
            help='Maximum number of retry attempts per order (default: 10)'
        )
        parser.add_argument(
            '--max-age-hours',
            type=int,
            default=24,
            help='Maximum age in hours before cancelling order (default: 24)'
        )

    def handle(self, *args, **options):
        max_retries = options['max_retries']
        max_age_hours = options['max_age_hours']
        
        self.stdout.write('Starting retry process for unassigned orders...')
        
        result = delivery_service.retry_unassigned_orders(
            max_retries=max_retries,
            max_age_hours=max_age_hours
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Retry process completed. Retried: {result["retried"]}, Assigned: {result["assigned"]}'
            )
        )
