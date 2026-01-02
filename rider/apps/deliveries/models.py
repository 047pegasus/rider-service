from apps.core.models import TimeStampedUUIDModel
from django.contrib.postgres.fields import ArrayField
from django.db import models
import json

# Create your models here.
class Delivery(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("assigned", "Assigned"),
        ("accepted", "Accepted"),
        ("denied", "Denied"),
        ("in_progress", "In Progress"),
        ("collected", "Collected"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="deliveries"
    )
    rider = models.ForeignKey(
        "riders.Rider", on_delete=models.CASCADE, related_name="deliveries"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="assigned")
    distance = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    # Simulation state persistence
    current_route_index = models.IntegerField(default=0, help_text='Current position in route for simulation')
    simulation_status = models.CharField(
        max_length=50, 
        default='idle',
        help_text='Simulation status: idle, going_to_pickup, at_pickup, going_to_delivery, completed'
    )
    last_location_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    last_location_lng = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)

    class Meta:
        db_table = "deliveries"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["rider"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self):
        return f"Delivery {self.id} - {self.order.order_number}"


class BatchDelivery(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    rider = models.ForeignKey(
        "riders.Rider", on_delete=models.CASCADE, related_name="batch_deliveries"
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="active")
    sequence = ArrayField(models.IntegerField(), default=list, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "batch_deliveries"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["rider"]),
        ]


class DeadLetterQueue(TimeStampedUUIDModel):
    """Model to store failed Kafka events for retry"""
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("retrying", "Retrying"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]
    
    topic = models.CharField(max_length=255, help_text="Kafka topic name")
    event_data = models.JSONField(help_text="Original event data")
    error_message = models.TextField(null=True, blank=True, help_text="Error that caused the failure")
    retry_count = models.IntegerField(default=0, help_text="Number of retry attempts")
    max_retries = models.IntegerField(default=5, help_text="Maximum number of retries")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    next_retry_at = models.DateTimeField(null=True, blank=True, help_text="When to retry next")
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "dead_letter_queue"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["next_retry_at"]),
            models.Index(fields=["topic"]),
        ]
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"DLQ Entry {self.id} - {self.topic} - {self.status}"
