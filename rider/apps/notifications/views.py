from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ViewSet):
    def list(self, request):
        notification = Notification.objects.all()
        serializer = NotificationSerializer(notification, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        notification = Notification.objects.get(pk=pk)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

    def create(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        notification = Notification.objects.get(pk=pk)
        serializer = NotificationSerializer(notification, data=request.data)
        if serializer.is_valid():
            serializer.update(notification, serializer.validated_data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        notification = Notification.objects.get(pk=pk)
        serializer = NotificationSerializer(
            notification, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.update(notification, serializer.validated_data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        notification = Notification.objects.get(pk=pk)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
