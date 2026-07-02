from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


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

        Every email in GramaCart should use this method.
        """

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