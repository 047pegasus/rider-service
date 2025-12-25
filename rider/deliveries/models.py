from django.db import models

from core.models import BaseModel


# Create your models here.
class Delivery(BaseModel):
    id = models.AutoField(primary_key=True)
