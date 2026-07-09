import logging
import requests

from django.conf import settings
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

        if not recipients:
            return False

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

            try:

                response = requests.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers=headers,
                    json=payload,
                    timeout=20,
                )

                response.raise_for_status()

                logger.info(
                    "Email sent successfully to %s",
                    recipient,
                )

            except Exception:

                logger.exception(
                    "Failed sending email to %s",
                    recipient,
                )

                success = False

        return success