from config.models import TimeStampedUUIDModel
from django.db import models


class Rider(TimeStampedUUIDModel):
    VEHICLE_TYPES = [
        ("bike", "Bike"),
        ("car", "Car"),
        ("scooter", "Scooter"),
    ]
    STATUS_CHOICES = [
        ("offline", "Offline"),
        ("busy", "Busy"),
        ("available", "Available"),
    ]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, unique=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPES)
    is_active = models.BooleanField(default=True)
    current_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="offline"
    )

    class Meta:
        db_table = "riders"
        indexes = [
            models.Index(fields=["current_status"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} - ({self.phone})"


class RiderLocation(models.Model):
    rider = models.ForeignKey(Rider, on_delete=models.CASCADE, related_name="locations")
    delivery = models.ForeignKey(
        "deliveries.Delivery",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rider_locations",
    )
    lat = models.DecimalField(max_digits=10, decimal_places=8)
    lng = models.DecimalField(max_digits=10, decimal_places=8)
    accuracy = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    speed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    heading = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    battery_level = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rider_locations"
        indexes = [
            models.Index(fields=["rider", "-timestamp"]),
            models.Index(fields=["delivery"]),
        ]
        ordering = ["-timestamp"]
