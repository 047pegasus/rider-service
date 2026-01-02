"""
Django management command to create Kafka topics
"""
from django.core.management.base import BaseCommand
from confluent_kafka.admin import AdminClient, NewTopic
from django.conf import settings
from apps.deliveries.constants import KAFKA_TOPICS


class Command(BaseCommand):
    help = 'Creates all required Kafka topics for the rider service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--partitions',
            type=int,
            default=3,
            help='Number of partitions for each topic (default: 3)',
        )
        parser.add_argument(
            '--replication-factor',
            type=int,
            default=1,
            help='Replication factor for each topic (default: 1)',
        )

    def handle(self, *args, **options):
        partitions = options['partitions']
        replication_factor = options['replication_factor']

        if not settings.KAFKA_BOOTSTRAP_SERVERS:
            self.stdout.write(
                self.style.ERROR('KAFKA_BOOTSTRAP_SERVERS not configured in settings')
            )
            return

        admin_client = AdminClient({
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS
        })

        topics_to_create = []
        for topic_name, topic_value in KAFKA_TOPICS.items():
            topics_to_create.append(
                NewTopic(
                    topic_value,
                    num_partitions=partitions,
                    replication_factor=replication_factor
                )
            )
            self.stdout.write(f'Preparing to create topic: {topic_value}')

        # Create topics
        futures = admin_client.create_topics(topics_to_create)

        # Wait for topics to be created
        created_count = 0
        for topic_name, future in futures.items():
            try:
                future.result()  # Wait for the topic to be created
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created topic: {topic_name}')
                )
                created_count += 1
            except Exception as e:
                if 'already exists' in str(e).lower() or 'TopicExistsException' in str(type(e)):
                    self.stdout.write(
                        self.style.WARNING(f'Topic {topic_name} already exists')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to create topic {topic_name}: {e}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! {created_count}/{len(KAFKA_TOPICS)} topics created/verified.'
            )
        )
