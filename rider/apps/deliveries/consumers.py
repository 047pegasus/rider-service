"""
Kafka consumer for processing location update events
"""
import json
import threading
from confluent_kafka import Consumer, KafkaError
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.deliveries.models import Delivery
from apps.riders.services import rider_service


class LocationUpdateConsumer:
    """Consumes location update events from Kafka and broadcasts via WebSocket"""
    
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': f"{settings.KAFKA_GROUP_ID}_location_updates",
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True,
        })
        self.running = False
        self.thread = None
        
    def start(self):
        """Start consuming messages in a background thread"""
        from apps.deliveries.constants import KAFKA_TOPICS
        topic = KAFKA_TOPICS.get("RIDER_LOCATION_UPDATE")
        if not topic:
            return
        
        # Try to subscribe, but handle missing topic gracefully
        try:
            self.consumer.subscribe([topic])
            self.running = True
            self.thread = threading.Thread(target=self._consume_loop, daemon=True)
            self.thread.start()
            print(f"Location update consumer started for topic: {topic}")
        except Exception as e:
            print(f"Warning: Could not start location consumer for topic {topic}: {e}")
            print("Run 'python manage.py create_kafka_topics' to create the required topics.")
        
    def _consume_loop(self):
        """Main consumption loop"""
        channel_layer = get_channel_layer()
        
        while self.running:
            msg = self.consumer.poll(timeout=1.0)
            if msg is None:
                continue
                
            if msg.error():
                error_code = msg.error().code()
                if error_code == KafkaError._PARTITION_EOF:
                    continue
                elif error_code == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    print(f"Kafka topic not found. Please run: python manage.py create_kafka_topics")
                    # Wait a bit before retrying
                    import time
                    time.sleep(5)
                    continue
                else:
                    print(f"Kafka error: {msg.error()}")
                    continue
                    
            try:
                data = json.loads(msg.value().decode('utf-8'))
                self._process_location_update(data, channel_layer)
            except Exception as e:
                print(f"Error processing location update: {e}")
                
    def _process_location_update(self, data, channel_layer):
        """Process location update and broadcast via WebSocket"""
        rider_id = data.get('rider_id')
        delivery_id = data.get('delivery_id')
        location = data.get('location', {})
        
        if not rider_id or not channel_layer:
            return
            
        # Notify rider channel
        async_to_sync(channel_layer.group_send)(
            f"rider_{rider_id}",
            {
                "type": "location_update",
                "data": {
                    "location": location,
                    "delivery_id": delivery_id,
                    "rider_id": rider_id
                }
            }
        )
        
        # If delivery_id exists, notify order channel
        if delivery_id:
            try:
                delivery = Delivery.objects.get(id=delivery_id)
                async_to_sync(channel_layer.group_send)(
                    f"order_{delivery.order.id}",
                    {
                        "type": "location_update",
                        "data": {
                            "rider_id": rider_id,
                            "location": location,
                            "delivery_id": str(delivery_id)
                        }
                    }
                )
            except Delivery.DoesNotExist:
                pass
                
    def stop(self):
        """Stop consuming messages"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.consumer.close()


# Global consumer instance
location_consumer = LocationUpdateConsumer()
