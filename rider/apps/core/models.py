from config.models import TimeStampedModel, UUIDModel


class TimeStampedUUIDModel(UUIDModel, TimeStampedModel):
    """Abstract base model with both UUID and timestamps"""

    class Meta:
        abstract = True
