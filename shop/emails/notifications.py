from django.conf import settings

from .services import EmailService


class AdminNotificationService:
    """
    Sends notification emails to GramaCart administrators.
    """

    @staticmethod
    def new_order(order):
        """
        Notify administrators when a new order is placed.
        """

        recipients = getattr(
            settings,
            "ORDER_NOTIFICATION_EMAILS",
            [],
        )

        if not recipients:
            return

        EmailService.send(
            subject=f"🛒 New Order #{order.order_number}",
            template_name="emails/admin/new_order.html",
            context={
                "order": order,
            },
            recipients=recipients,
        )