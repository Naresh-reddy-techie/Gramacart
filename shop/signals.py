print(">>> shop.signals imported")

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from shop.models import Order
from shop.emails.notifications import AdminNotificationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def notify_admin_new_order(sender, instance, created, **kwargs):

    print(
        "Signal:",
        instance.order_number,
        "created =", created,
        "status =", instance.status,
    )

    if not created:
        return

    def send_notification():
        try:
            print("Calling AdminNotificationService...")
            AdminNotificationService.new_order(instance)
            print("Admin notification sent.")
        except Exception:
            logger.exception(
                "Failed to send admin notification for Order %s",
                instance.order_number,
            )

    transaction.on_commit(send_notification)