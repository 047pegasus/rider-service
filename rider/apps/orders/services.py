import json

from django.db import transaction

from apps.deliveries.models import Delivery
from apps.events.constants import EventTypes
from apps.events.services import event_service
from apps.riders.services import rider_service

from .models import Order


class OrderService:
    @staticmethod
    def create_order(order_data):
        try:
            with transaction.atomic():
                order = Order.objects.create(**order_data)
                # event_service.create_event(EventTypes.ORDER_RECEIVED, order.id)
                return order
        except Exception as e:
            return None

    @staticmethod
    def update_order_status(
        self, order_id, new_status, rider_id=None, delivery_id=None
    ):
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order_id)
                old_status = order.status
                order.status = new_status
                order.save()

                if delivery_id and rider_id:
                    event_type = (
                        EventTypes.ORDER_PREPARING
                        if new_status == "preparing"
                        else EventTypes.ORDER_READY
                        if new_status == "ready"
                        else EventTypes.ORDER_PICKED_UP
                        if new_status == "picked_up"
                        else EventTypes.ORDER_DELIVERED
                        if new_status == "delivered"
                        else EventTypes.ORDER_CANCELLED
                        if new_status == "cancelled"
                        else None
                    )
                    if event_type:
                        event_service.create_event(
                            delivery_id=delivery_id,
                            rider_id=rider_id,
                            event_type=event_type,
                            order_id=order_id,
                            event_data={
                                "old_status": old_status,
                                "new_status": new_status,
                            },
                        )
                return order
        except Exception as e:
            return None

    @staticmethod
    def get_order_tracking_info(order_id):
        try:
            order = Order.objects.get(id=order_id)
            delivery = Delivery.objects.filter(
                order_id=order_id, status="in_progress"
            ).first()
            if not delivery:
                return {
                    "order": order,
                    "status": order.status,
                    "delivery": None,
                    "rider": None,
                    "current_location": None,
                }

            rider_location = rider_service.get_rider_location(str(delivery.rider_id))
            if rider_location:
                return {
                    "order": order,
                    "status": order.status,
                    "delivery": delivery,
                    "rider": delivery.rider,
                    "current_location": rider_location,
                    "estimated_delivery": order.estimated_delivery_time,
                }
            else:
                return {
                    "order": order,
                    "status": order.status,
                    "delivery": delivery,
                    "rider": delivery.rider,
                    "current_location": None,
                    "estimated_delivery": order.estimated_delivery_time,
                }

        except Order.DoesNotExist:
            return None


order_service = OrderService()
