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
                # Set initial status to preparing
                order_data['status'] = 'preparing'
                order = Order.objects.create(**order_data)
                
                # Simulate order preparation time (30-60 seconds)
                import threading
                import time
                import random
                from django.utils import timezone
                
                def mark_ready():
                    prep_time = random.randint(30, 60)
                    time.sleep(prep_time)
                    try:
                        order.refresh_from_db()
                        if order.status == 'preparing':
                            order.status = 'ready'
                            order.save()
                            # Auto-assign rider when order is ready
                            from apps.deliveries.models import Delivery
                            if not Delivery.objects.filter(order=order).exclude(status__in=['failed', 'completed']).exists():
                                from apps.deliveries.services import delivery_service
                                try:
                                    delivery_service.assign_delivery(str(order.id))
                                except Exception as e:
                                    print(f"Auto-assignment failed: {e}")
                                    # Order will be retried by the retry_unassigned_orders command
                    except Exception as e:
                        print(f"Error in mark_ready: {e}")
                
                # Start preparation timer in background
                prep_thread = threading.Thread(target=mark_ready, daemon=True)
                prep_thread.start()
                
                return order
        except Exception as e:
            print(f"Error creating order: {e}")
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
            # Check for any active delivery (assigned, in_progress, etc.)
            delivery = Delivery.objects.filter(
                order_id=order_id
            ).exclude(status__in=["completed", "failed"]).first()
            
            if not delivery:
                return {
                    "order": order,
                    "order_number": order.order_number,
                    "status": order.status,
                    "delivery": None,
                    "rider": None,
                    "current_location": None,
                    "estimated_delivery": order.estimated_delivery_time,
                }

            rider_location = rider_service.get_rider_location(str(delivery.rider_id))
            if rider_location:
                return {
                    "order": order,
                    "order_number": order.order_number,
                    "status": order.status,
                    "delivery": delivery,
                    "rider": delivery.rider,
                    "current_location": rider_location,
                    "estimated_delivery": order.estimated_delivery_time,
                }
            else:
                return {
                    "order": order,
                    "order_number": order.order_number,
                    "status": order.status,
                    "delivery": delivery,
                    "rider": delivery.rider,
                    "current_location": None,
                    "estimated_delivery": order.estimated_delivery_time,
                }

        except Order.DoesNotExist:
            return None


order_service = OrderService()
