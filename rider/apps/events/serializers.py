from rest_framework import serializers

from .models import DeliveryEvent


class DeliveryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryEvent
        fields = "__all__"
