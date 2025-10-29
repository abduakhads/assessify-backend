# myapp/email.py

from djoser.email import ActivationEmail, PasswordResetEmail
from django.conf import settings


class AwesomeActivationEmail(ActivationEmail):
    template_name = "email/activation.html"
    subject_template_name = None  # get_subject

    def get_subject(self):
        site_name = getattr(settings, "DJOSER", {}).get(
            "EMAIL_FRONTEND_SITE_NAME", "Assessify"
        )
        return f"Activate your {site_name} account"

    def get_context_data(self):
        context = super().get_context_data()

        protocol = "https" if not settings.DEBUG else "http"
        backend_domain = getattr(settings, "DJOSER", {}).get(
            "EMAIL_BACKEND_DOMAIN", "localhost:8000"
        )
        static_url = settings.STATIC_URL

        context.update(
            {
                "site_name": getattr(settings, "DJOSER", {}).get(
                    "EMAIL_FRONTEND_SITE_NAME", "Assessify"
                ),
                "protocol": protocol,
                "domain": backend_domain,
                "static_url": static_url,
            }
        )

        if "uid" in context and "token" in context:
            frontend_domain = getattr(settings, "DJOSER", {}).get(
                "EMAIL_FRONTEND_DOMAIN", "localhost:3000"
            )
            activation_path = getattr(settings, "DJOSER", {}).get(
                "ACTIVATION_URL", "auth/activate/{uid}/{token}"
            )

            formatted_path = activation_path.format(
                uid=context["uid"], token=context["token"]
            )

            context["activation_url"] = (
                f"{protocol}://{frontend_domain}/{formatted_path}"
            )

        return context


class AwesomePasswordResetEmail(PasswordResetEmail):
    template_name = "email/reset_password.html"
    subject_template_name = None  # get_subject

    def get_subject(self):
        site_name = getattr(settings, "DJOSER", {}).get(
            "EMAIL_FRONTEND_SITE_NAME", "Assessify"
        )
        return f"Reset your {site_name} password"

    def get_context_data(self):
        context = super().get_context_data()

        protocol = "https" if not settings.DEBUG else "http"
        backend_domain = getattr(settings, "DJOSER", {}).get(
            "EMAIL_BACKEND_DOMAIN", "localhost:8000"
        )
        static_url = settings.STATIC_URL

        context.update(
            {
                "site_name": getattr(settings, "DJOSER", {}).get(
                    "EMAIL_FRONTEND_SITE_NAME", "Assessify"
                ),
                "protocol": protocol,
                "domain": backend_domain,
                "static_url": static_url,
            }
        )

        if "uid" in context and "token" in context:
            frontend_domain = getattr(settings, "DJOSER", {}).get(
                "EMAIL_FRONTEND_DOMAIN", "localhost:3000"
            )
            password_reset_path = getattr(settings, "DJOSER", {}).get(
                "PASSWORD_RESET_CONFIRM_URL", "reset/password/confirm/{uid}/{token}"
            )

            formatted_path = password_reset_path.format(
                uid=context["uid"], token=context["token"]
            )

            context["password_reset_url"] = (
                f"{protocol}://{frontend_domain}/{formatted_path}"
            )

        return context
