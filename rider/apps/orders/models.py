from apps.core.models import TimeStampedUUIDModel
from django.db import models


class Order(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("preparing", "Preparing"),
        ("ready", "Ready"),
        ("picked_up", "Picked Up"),
        ("in_transit", "In Transit"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    order_number = models.CharField(max_length=100, unique=True)
    customer_id = models.UUIDField()
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=10)
    pickup_address = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )
    pickup_lng = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )
    delivery_address = models.CharField(max_length=255)
    delivery_lat = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )
    delivery_lng = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True
    )
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default="pending")
    priority = models.IntegerField(default=0)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    special_instructions = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["customer_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["order_number"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return f"Order #{self.order_number} - {self.status}"
