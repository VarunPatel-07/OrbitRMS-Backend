from arq import create_pool

from config.EnvConfig import EnvConfig
from mailer.emailService.connection import get_arq_connection_setting
from mailer.emailService.email_idempotency import generate_email_idempotency_key
from mailer.emailService.email_models import EmailQueuePayload, EmailSchema

EMAIL_ARQ_QUEUE_NAME = f"orbitrms:{EnvConfig.BACKEND_APP_ENVIRONMENT.lower()}:email:arq"


def build_email_queue_payload(email_data: EmailSchema) -> EmailQueuePayload:

    return EmailQueuePayload(
        recipients_email=email_data.recipients_email,
        subject=email_data.subject,
        body=email_data.body,
        email_type=email_data.email_type,
        idempotency_key=generate_email_idempotency_key(email_data),
        max_retries=email_data.max_retries,
        metadata=email_data.metadata,
    )


async def email_sender_function(email_data: EmailSchema) -> dict:
    payload = build_email_queue_payload(email_data)

    queue_connection = await create_pool(get_arq_connection_setting(), default_queue_name=EMAIL_ARQ_QUEUE_NAME)

    try:
        job = await queue_connection.enqueue_job(
            "send_email_worker",
            payload.model_dump(),
            _job_id=payload.idempotency_key,
            _queue_name=EMAIL_ARQ_QUEUE_NAME,
        )

        if job is None:
            return {
                "message": "Email job already queued or completed",
                "success": True,
                "deduplicated": True,
                "job_id": payload.idempotency_key,
            }

        return {
            "message": "Email job queued successfully",
            "success": True,
            "deduplicated": False,
            "job_id": job.job_id,
            "queue_name": EMAIL_ARQ_QUEUE_NAME,
        }
    finally:
        await queue_connection.close()
