from apps.core.models import TimeStampedUUIDModel
from django.contrib.postgres.fields import ArrayField
from django.db import models

# Create your models here.
class Delivery(TimeStampedUUIDModel):
    STATUS_CHOICES = [
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
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
