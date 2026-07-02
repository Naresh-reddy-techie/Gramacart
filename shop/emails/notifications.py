from django.conf import settings

from .services import EmailService


class AdminNotificationService:
    """
    Handles all emails sent to GramaCart administrators.
    """

    @staticmethod
    def new_order(order):

        EmailService.send(

            subject=f"🛒 New Order #{order.order_number}",

            template_name="emails/admin/new_order.html",

            context={
                "order": order,
            },

            recipients=settings.ORDER_NOTIFICATION_EMAILS,

        )