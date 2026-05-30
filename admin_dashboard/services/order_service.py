from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from shop.models import Order
from delivery_portal.models import Delivery, DeliveryStatus
from admin_dashboard.models import ShippingCost
from delivery_portal.utils import prepare_delivery_for_radar




class OrderService:

    @staticmethod
    @transaction.atomic
    def pack_order(order):

        # Update order
        order.status = 'packed'

        order.save(
            update_fields=['status']
        )

        # Create delivery
        delivery, created = (
            Delivery.objects.get_or_create(
                order=order
            )
        )

        # IMPORTANT:
        # Prepare for radar marketplace
        prepare_delivery_for_radar(
            delivery.id
        )

        return delivery

class InvoiceService:

    @staticmethod
    def get_invoice_data(order):
        return {
            "order": order,
            "items": order.items.all(),
            "subtotal": order.subtotal,
            "shipping": order.shipping_cost,
            "total": order.total,
        }
    
class PDFService:

    @staticmethod
    def generate_invoice_pdf(order):
        # reuse InvoiceService data
        data = InvoiceService.get_invoice_data(order)

        # build PDF here (ReportLab / WeasyPrint)
        return pdf_file