from django.apps import AppConfig


class DeliveriesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.deliveries'

    def ready(self):
        """Start Kafka consumer when app is ready"""
        try:
            from apps.deliveries.consumers import location_consumer
            # Delay start slightly to allow Kafka to be ready
            import threading
            import time
            
            def delayed_start():
                time.sleep(2)  # Wait 2 seconds for Kafka to be ready
                try:
                    location_consumer.start()
                except Exception as e:
                    print(f"Failed to start location consumer: {e}")
                    print("Note: If topics don't exist, run: python manage.py create_kafka_topics")
            
            thread = threading.Thread(target=delayed_start, daemon=True)
            thread.start()
        except Exception as e:
            print(f"Failed to initialize location consumer: {e}")
            print("Note: If topics don't exist, run: python manage.py create_kafka_topics")
