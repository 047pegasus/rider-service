from rest_framework import status, viewsets

from .models import DeliveryEvent
from .serializers import DeliveryEventSerializer


class DeliveryEventViewSet(viewsets.ViewSet):
    def list(self, request):
        queryset_delivery_events = DeliveryEvent.objects.all()
        serializer = DeliveryEventSerializer(queryset_delivery_events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        queryset_delivery_events = DeliveryEvent.objects.all()
        delivery_event = queryset_delivery_events.filter(id=pk).first()
        if delivery_event is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = DeliveryEventSerializer(delivery_event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = DeliveryEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        queryset_delivery_events = DeliveryEvent.objects.all()
        delivery_event = queryset_delivery_events.filter(id=pk).first()
        if delivery_event is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = DeliveryEventSerializer(delivery_event, data=request.data)
        if serializer.is_valid():
            serializer.update(delivery_event, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        queryset_delivery_events = DeliveryEvent.objects.all()
        delivery_event = queryset_delivery_events.filter(id=pk).first()
        if delivery_event is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = DeliveryEventSerializer(
            delivery_event, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.update(delivery_event, serializer.validated_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        queryset_delivery_events = DeliveryEvent.objects.all()
        delivery_event = queryset_delivery_events.filter(id=pk).first()
        if delivery_event is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        delivery_event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
