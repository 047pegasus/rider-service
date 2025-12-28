from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import BatchDelivery, Delivery
from .serializers import BatchDeliverySerializer, DeliverySerializer


class DeliveryViewSet(viewsets.ViewSet):
    def list(self, request):
        deliveries = Delivery.objects.all()
        serializer = DeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        delivery = Delivery.objects.get(pk=pk)
        serializer = DeliverySerializer(delivery)
        if serializer.is_valid():
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        delivery = Delivery.objects.get(pk=pk)
        serializer = DeliverySerializer(delivery, data=request.data)
        if serializer.is_valid():
            serializer.update(delivery, serializer.validated_data)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        delivery = Delivery.objects.get(pk=pk)
        serializer = DeliverySerializer(delivery, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.update(delivery, serializer.validated_data)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        delivery = Delivery.objects.get(pk=pk)
        delivery.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BatchDeliveryViewSet(viewsets.ViewSet):
    def create(self, request):
        serializer = BatchDeliverySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        batch_delivery = BatchDelivery.objects.get(pk=pk)
        serializer = BatchDeliverySerializer(batch_delivery, data=request.data)
        if serializer.is_valid():
            serializer.update(batch_delivery, serializer.validated_data)
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        batch_delivery = BatchDelivery.objects.get(pk=pk)
        batch_delivery.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
