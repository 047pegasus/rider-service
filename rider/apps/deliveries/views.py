from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Delivery
from .serializers import DeliverySerializer
from .services import delivery_service


class DeliveryViewSet(viewsets.ViewSet):
    def list(self, request):
        deliveries = Delivery.objects.all()
        serializer = DeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            delivery = Delivery.objects.get(pk=pk)
            serializer = DeliverySerializer(delivery)
            if serializer.is_valid():
                return Response(serializer.data)
        except Delivery.DoesNotExist:
            return Response(
                {"detail": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def assign(self, request):
        order_id = request.data.get("order_id")
        if not order_id:
            return Response(
                {"detail": "Order ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            delivery = delivery_service.assign_delivery(order_id)
            return Response(
                DeliverySerializer(delivery).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["put"])
    def update_status(self, request, pk=None):
        try:
            new_status = request.data.get("status")
            location = request.data.get("location")
            delivery = delivery_service.update_delivery_status(pk, new_status, location)
            return Response(
                DeliverySerializer(delivery).data, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
