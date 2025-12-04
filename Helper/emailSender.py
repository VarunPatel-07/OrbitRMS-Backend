import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from pydantic import BaseModel

from Config.EnvConfig import EnvConfig

load_dotenv(override=True)


# pydantic model to verify the incoming email data
class EmailSchema(BaseModel):
    recever_email: str | List[str]
    subject: str
    body: Optional[str]


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


def email_sender_function(email_data: EmailSchema, background_task: BackgroundTasks):
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
