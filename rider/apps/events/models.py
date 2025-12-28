from apps.core.models import TimeStampedUUIDModel
from django.db import models


class DeliveryEvent(TimeStampedUUIDModel):
    EVENT_TYPE_CHOICES = [
        ("order_received", "ORDER_RECEIVED"),
        ("preparing", "Preparing"),
        ("ready_to_deliver", "Ready to Deliver"),
        ("rider_assigned", "Rider Assigned"),
        ("pickup_started", "Pickup Started"),
        ("picked_up", "Picked Up"),
        ("in_transit", "In Transit"),
        ("nearby", "Nearby"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    rider = models.ForeignKey(
        "riders.Rider", on_delete=models.CASCADE, related_name="events"
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="events"
    )
    delivery = models.ForeignKey(
        "deliveries.Delivery", on_delete=models.CASCADE, related_name="events"
    )
    event_type = models.CharField(max_length=100, choices=EVENT_TYPE_CHOICES)
    event_data = models.JSONField(default=dict, blank=True)
    location_lat = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )
    location_long = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "delivery_events"
        indexes = [
            models.Index(fields=["delivery"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_type} - {self.delivery.id}"
