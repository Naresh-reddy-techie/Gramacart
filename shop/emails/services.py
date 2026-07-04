import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


logger = logging.getLogger(__name__)


class EmailService:

    @staticmethod
    def send(
        *,
        subject,
        template_name,
        context,
        recipients,
    ):
        """
        Generic email sender.

        Returns:
            True  -> email sent successfully
            False -> sending failed
        """

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

            email.send(
                fail_silently=False
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