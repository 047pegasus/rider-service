from django.core.serializers.base import SerializationError
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Rider, RiderLocation
from .serializers import RiderLocationSerializer, RiderSerializer


class RiderViewSet(viewsets.ViewSet):
    def list(self, request):
        riders = Rider.objects.all()
        serializer = RiderSerializer(riders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        rider = Rider.objects.get(id=pk)
        serializer = RiderSerializer(rider)
        return Response(serializer.data)

    def create(self, request):
        serializer = RiderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        rider = Rider.objects.get(id=pk)
        serializer = RiderSerializer(rider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        rider = Rider.objects.get(id=pk)
        serializer = RiderSerializer(rider, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        rider = Rider.objects.get(id=pk)
        rider.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RiderLocationsViewSet(viewsets.ViewSet):
    def list(self, request):
        locations = RiderLocation.objects.all()
        print("All Rider locations", locations)
        serializer = RiderLocationSerializer(locations, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        location = RiderLocation.objects.get(id=pk)
        serializer = RiderLocationSerializer(location)
        return Response(serializer.data)

    def create(self, request):
        serializer = RiderLocationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        location = RiderLocation.objects.get(id=pk)
        serializer = RiderLocationSerializer(location, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        location = RiderLocation.objects.get(id=pk)
        serializer = RiderLocationSerializer(location, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        location = RiderLocation.objects.get(id=pk)
        location.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
