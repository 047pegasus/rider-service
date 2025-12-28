from django.contrib import admin

from .models import BatchDelivery, Delivery

admin.site.register(Delivery)
admin.site.register(BatchDelivery)
