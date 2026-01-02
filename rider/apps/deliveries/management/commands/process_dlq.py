"""
Management command to process Dead Letter Queue entries.
This should be run periodically to retry failed Kafka events.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.deliveries.models import DeadLetterQueue
from infrastructure.kafka_client import kafka_client


class Command(BaseCommand):
    help = 'Process Dead Letter Queue entries and retry failed Kafka events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-retries',
            type=int,
            default=5,
            help='Maximum number of retry attempts per event (default: 5)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of DLQ entries to process in one run (default: 100)'
        )

    def handle(self, *args, **options):
        max_retries = options['max_retries']
        batch_size = options['batch_size']
        
        self.stdout.write('Processing Dead Letter Queue entries...')
        
        # Get pending entries that are ready for retry
        now = timezone.now()
        pending_entries = DeadLetterQueue.objects.filter(
            status='pending',
            next_retry_at__lte=now,
            retry_count__lt=max_retries
        )[:batch_size]
        
        processed = 0
        succeeded = 0
        failed = 0
        
        for entry in pending_entries:
            try:
                # Mark as retrying
                entry.status = 'retrying'
                entry.save()
                
                # Attempt to republish
                success = kafka_client.publish(
                    topic=entry.topic,
                    event_data=entry.event_data
                )
                
                if success:
                    # Mark as processed
                    entry.status = 'processed'
                    entry.processed_at = timezone.now()
                    entry.save()
                    succeeded += 1
                else:
                    # Increment retry count and calculate next retry time
                    entry.retry_count += 1
                    backoff_minutes = min(2 ** entry.retry_count, 60)  # Cap at 60 minutes
                    entry.next_retry_at = timezone.now() + timedelta(minutes=backoff_minutes)
                    
                    if entry.retry_count >= max_retries:
                        entry.status = 'failed'
                    else:
                        entry.status = 'pending'
                    entry.save()
                    failed += 1
                
                processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing DLQ entry {entry.id}: {e}')
                )
                entry.status = 'failed'
                entry.error_message = str(e)
                entry.save()
                failed += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'DLQ processing completed. Processed: {processed}, Succeeded: {succeeded}, Failed: {failed}'
            )
        )
