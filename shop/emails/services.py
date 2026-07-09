import logging
import requests

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    Centralized email sending service using Brevo API.
    """

    @staticmethod
    def send(
        *,
        subject,
        template_name,
        context,
        recipients,
    ):

        if not recipients:
            logger.warning("Recipient list is empty.")
            return False

        try:
            html_content = render_to_string(
                template_name,
                context,
            )

            text_content = strip_tags(html_content)

            headers = {
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            }

            success = True

            for recipient in recipients:

                payload = {
                    "sender": {
                        "name": "GramaCart",
                        "email": settings.DEFAULT_FROM_EMAIL,
                    },
                    "to": [
                        {
                            "email": recipient,
                        }
                    ],
                    "subject": subject,
                    "htmlContent": html_content,
                    "textContent": text_content,
                }

                response = requests.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers=headers,
                    json=payload,
                    timeout=20,
                )

                print("Brevo Status:", response.status_code)
                print("Brevo Response:", response.text)

                response.raise_for_status()

                logger.info(
                    "Email sent successfully to %s",
                    recipient,
                )

            return success

        except Exception:
            logger.exception(
                "Failed to send email '%s'",
                subject,
            )
            return False