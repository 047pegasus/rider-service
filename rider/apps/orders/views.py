from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ViewSet):
    def list(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        if serializer.is_valid():
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=id):
        order = Order.objects.get(id=pk)
        serializer = OrderSerializer(order)
        if serializer.is_valid():
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=400)

    def create(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        else:
            return Response(serializer.errors, status=400)

    def update(self, request, pk=id):
        order = Order.objects.get(id=pk)
        serializer = OrderSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.update(order, serializer.validated_data)
            return Response(serializer.data, status=200)
        else:
            return Response(serializer.errors, status=400)

    def partial_update(self, request, pk=id):
        order = Order.objects.get(id=pk)
        serializer = OrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.update(order, serializer.validated_data)
            return Response(serializer.data, status=200)
        else:
            return Response(serializer.errors, status=400)

    def destroy(self, request, pk=id):
        order = Order.objects.get(id=pk)
        order.delete()
        return Response(status=204)
