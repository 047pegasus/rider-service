from gzip import READ

from apps.core.models import TimeStampedUUIDModel
from django.db import models


class Notification(TimeStampedUUIDModel):
    RECIPIENT_TYPE_CHOICES = [
        ("customer", "Customer"),
        ("rider", "Rider"),
    ]

    recipient_id = models.UUIDField()
    recipient_type = models.CharField(max_length=50, choices=RECIPIENT_TYPE_CHOICES)
    delivery = models.ForeignKey(
        "deliveries.Delivery",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=100)
    title = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["recipient_id", "is_read"]),
        ]
        ordering = ["-sent_at"]
