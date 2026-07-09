import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Centralized email sending service.

    Every email in GramaCart should use this service.
    """

    @staticmethod
    def send(
        *,
        subject,
        template_name,
        context,
        recipients,
    ):
        """
        Send an HTML + plain text email.

        Returns:
            True  -> Email sent successfully.
            False -> Email sending failed.
        """

        if not recipients:
            logger.warning(
                "Email not sent because recipient list is empty."
            )
            return False

        try:
            html_content = render_to_string(
                template_name,
                context,
            )

            text_content = strip_tags(
                html_content
            )

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )

            email.attach_alternative(
                html_content,
                "text/html",
            )

            import socket

            try:
                print("Testing SMTP connection...")
                s = socket.create_connection(("smtp-relay.brevo.com", 587), 10)
                print("SMTP CONNECTION SUCCESS")
                s.close()
            except Exception as e:
                print("SMTP CONNECTION FAILED:", repr(e))

            email.send(
                fail_silently=False,
            )

            logger.info(
                "Email sent successfully to %s",
                recipients,
            )

            return True

        except Exception:
            logger.exception(
                "Failed to send email '%s' to %s",
                subject,
                recipients,
            )

            return False