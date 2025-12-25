from django.db import models


class BaseModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Set abstract=True so Django knows not to create a
        # separate database table for this model.
        abstract = True
        # Optional: You can also set default ordering here
        ordering = ["-created_at"]
