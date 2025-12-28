from rest_framework import serializers
from .models import Rider, RiderLocation

class RiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rider
        fields = '__all__'

class RiderLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiderLocation
        fields = '__all__'
