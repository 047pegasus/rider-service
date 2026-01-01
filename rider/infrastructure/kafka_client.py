import json

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

    def publish(self, topic: str, event_data: dict):
        try:
            self.producer.produce(topic, value=json.dumps(event_data).encode("utf-8"))
            self.producer.flush()
        except KafkaError as e:
            print(f"Kafka error: {e}")
            return False

    def close(self):
        self.producer.flush()
        self.consumer.close()


kafka_client = KafkaClient()
