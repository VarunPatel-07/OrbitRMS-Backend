import json
import time
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from sib_api_v3_sdk.rest import ApiException
import sib_api_v3_sdk
from config.EnvConfig import EnvConfig
from mailer.emailService.email_models import EmailSchema


class TemporaryEmailSendError(Exception):
    """This is an class that is used for raising the Temporary Email Send Error"""


class PermanentEmailSendError(Exception):
    """This is an class that is used for raising the Permanent Email Send Error"""

    config = None


if EnvConfig.BACKEND_APP_ENVIRONMENT == "DEVELOPMENT":
    config = ConnectionConfig(
        MAIL_USERNAME=EnvConfig.EMAIL_ADDRESS,
        MAIL_PASSWORD=EnvConfig.GOOGLE_APP_PASSWORD,
        MAIL_FROM=EnvConfig.EMAIL_ADDRESS,
        MAIL_FROM_NAME="OrbitRMS",
        MAIL_PORT=int(EnvConfig.EMAIL_PORT),
        MAIL_SERVER=EnvConfig.EMAIL_SERVER_ADDRESS,
        MAIL_SSL_TLS=True,  # Enable SSL for port 465
        MAIL_STARTTLS=False,  # Disable STARTTLS for port 465
        USE_CREDENTIALS=True,
        TIMEOUT=90,
    )
elif EnvConfig.BACKEND_APP_ENVIRONMENT == "PRODUCTION":
    config = ConnectionConfig(
        MAIL_USERNAME=EnvConfig.BREVO_SMTP_USERNAME,
        MAIL_PASSWORD=EnvConfig.BREVO_SMTP_PASSWORD,
        MAIL_FROM=EnvConfig.BREVO_FROM_EMAIL,
        MAIL_FROM_NAME="OrbitRMS",
        MAIL_PORT=int(EnvConfig.BREVO_SMTP_PORT),
        MAIL_SERVER=EnvConfig.BREVO_SMTP_SERVER,
        MAIL_SSL_TLS=False,  # For port 587
        MAIL_STARTTLS=True,  # STARTTLS must be True for Brevo 587
        USE_CREDENTIALS=True,
        TIMEOUT=90,
    )
else:
    config = None


async def send_smtp_mail_function(email_data: EmailSchema, job_try: int = 1) -> dict:
    if email_data.metadata.get("permanent_failure"):
        raise PermanentEmailSendError("simulated permanent email failure")

    fail_until_try = int(email_data.metadata.get("fail_until_try", 0) or 0)

    if job_try <= fail_until_try:
        raise TemporaryEmailSendError(f"simulated temporary email failure until try {fail_until_try}")

    if EnvConfig.BACKEND_APP_ENVIRONMENT in ["DEVELOPMENT", "PRODUCTION"]:
        try:
            # create the email message
            message = MessageSchema(
                subject=email_data.subject,
                recipients=(
                    [email_data.recipients_email]
                    if isinstance(email_data.recipients_email, str)
                    else email_data.recipients_email
                ),
                body=email_data.body,
                subtype="html",
            )

            fast_mail = FastMail(config)

            await fast_mail.send_message(message=message)

            return {"message": "Email sent successfully!", "success": True}

        except Exception as e:

            return {
                "message": "unable to send Email Try Again Letter",
                "success": False,
                "error": str(e),
            }
    else:
        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = EnvConfig.BREVO_HTTP_API_KEY

            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender={"name": "OrbitRMS", "email": EnvConfig.BREVO_FROM_EMAIL},
                to=(
                    [{"email": email_data.recipients_email}]
                    if isinstance(email_data.recipients_email, str)
                    else [{"email": email} for email in email_data.recipients_email]
                ),
                subject=email_data.subject,
                html_content=email_data.body,
            )

            api_instance.send_transac_email(send_smtp_email=send_smtp_email)

            return {"message": "Email sent via Brevo HTTP API", "success": True}
        except ApiException as e:
            raise Exception(f"Brevo API error: {str(e)}")

        except Exception as e:
            raise Exception(f"Email sending error: {str(e)}")
