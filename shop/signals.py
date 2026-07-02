import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from shop.models import Order
from shop.emails.notifications import AdminNotificationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def notify_admin_new_order(sender, instance, created, **kwargs):

    if not created:
        return

    def send_notification():
        try:
            AdminNotificationService.new_order(instance)
        except Exception:
            logger.exception(
                "Failed to send admin notification for Order %s",
                instance.order_number,
            )

    transaction.on_commit(send_notification)