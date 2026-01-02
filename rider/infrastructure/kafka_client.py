import json
from django.utils import timezone
from datetime import timedelta

from confluent_kafka import Consumer, Producer
from confluent_kafka.error import KafkaError
from django.conf import settings


class KafkaClient:
    def __init__(self):
        self.producer = Producer(
            {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "client.id": settings.KAFKA_CLIENT_ID,
            }
        )
        self.consumer = Consumer(
            {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "auto.offset.reset": "earliest",
                "group.id": settings.KAFKA_GROUP_ID,
            }
        )

    def publish(self, topic: str, event_data: dict, partition=None, key=None):
        """Publish event to Kafka topic, with automatic DLQ on failure"""
        delivery_failed = {'failed': False, 'error': None}
        
        def delivery_callback(err, msg):
            """Callback for message delivery"""
            if err is not None:
                delivery_failed['failed'] = True
                delivery_failed['error'] = str(err)
                print(f"Message delivery failed: {err}")
                # Send to DLQ
                try:
                    self._send_to_dlq(topic, event_data, str(err))
                except Exception as e:
                    print(f"Error sending to DLQ: {e}")
        
        try:
            # Use delivery_id or rider_id as partition key for better distribution
            event_json = json.dumps(event_data)
            
            # Prepare produce arguments - only include partition if it's not None
            produce_kwargs = {
                'value': event_json.encode("utf-8"),
                'callback': delivery_callback
            }
            
            if key:
                produce_kwargs['key'] = key.encode('utf-8') if isinstance(key, str) else key
            
            # Only add partition if it's not None (Kafka doesn't accept None for partition)
            if partition is not None:
                produce_kwargs['partition'] = partition
            
            self.producer.produce(topic, **produce_kwargs)
            self.producer.poll(0)  # Trigger delivery callbacks
            self.producer.flush(timeout=5)
            
            if delivery_failed['failed']:
                return False
            return True
        except KafkaError as e:
            print(f"Kafka error: {e}")
            self._send_to_dlq(topic, event_data, str(e))
            return False
        except Exception as e:
            print(f"Unexpected error publishing to Kafka: {e}")
            self._send_to_dlq(topic, event_data, str(e))
            return False

    def _send_to_dlq(self, topic: str, event_data: dict, error_message: str):
        """Send failed event to Dead Letter Queue"""
        try:
            from apps.deliveries.models import DeadLetterQueue
            
            # Calculate next retry time (exponential backoff)
            retry_count = 0
            backoff_minutes = min(2 ** retry_count, 60)  # Cap at 60 minutes
            next_retry_at = timezone.now() + timedelta(minutes=backoff_minutes)
            
            DeadLetterQueue.objects.create(
                topic=topic,
                event_data=event_data,
                error_message=error_message,
                retry_count=retry_count,
                status='pending',
                next_retry_at=next_retry_at
            )
            print(f"Event sent to DLQ: {topic}")
        except Exception as e:
            print(f"Error creating DLQ entry: {e}")

    def close(self):
        self.producer.flush()
        self.consumer.close()


kafka_client = KafkaClient()
