import os
from typing import List, Optional

import sib_api_v3_sdk
from dotenv import load_dotenv
from fastapi import BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from pydantic import BaseModel
from sib_api_v3_sdk.rest import ApiException

from config.EnvConfig import EnvConfig

load_dotenv(override=True)


# pydantic model to verify the incoming email data
class EmailSchema(BaseModel):
    recever_email: str | List[str]
    subject: str
    body: Optional[str]


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


def email_sender_function(email_data: EmailSchema, background_task: BackgroundTasks):
    if EnvConfig.BACKEND_APP_ENVIRONMENT in ["DEVELOPMENT", "PRODUCTION"]:
        try:
            # create the email message
            message = MessageSchema(
                subject=email_data.subject,
                recipients=(
                    [email_data.recever_email]
                    if isinstance(email_data.recever_email, str)
                    else email_data.recever_email
                ),
                body=email_data.body,
                subtype="html",
            )

            # create fast mail instance

            fast_mail = FastMail(config)

            # send mail in the background

            background_task.add_task(fast_mail.send_message, message)

            return {"message": "Email sent successfully!", "success": True}

        except Exception as e:

            return {
                "message": "unable to send Email Try Again Letter",
                "success": False,
                "error": str(e),
            }
    else:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = EnvConfig.BREVO_HTTP_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": "OrbitRMS", "email": EnvConfig.BREVO_FROM_EMAIL},
            to=(
                [{"email": email_data.recever_email}]
                if isinstance(email_data.recever_email, str)
                else [{"email": email} for email in email_data.recever_email]
            ),
            subject=email_data.subject,
            html_content=email_data.body,
        )

        # Run in background
        background_task.add_task(api_instance.send_transac_email, send_smtp_email)

        return {"message": "Email sent via Brevo HTTP API", "success": True}
