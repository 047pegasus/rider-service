from rest_framework import serializers

from .models import BatchDelivery, Delivery


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = "__all__"


class BatchDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = BatchDelivery
        fields = "__all__"
