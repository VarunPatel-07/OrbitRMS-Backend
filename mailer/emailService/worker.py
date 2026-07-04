from arq import Retry

from config.EnvConfig import EnvConfig
from mailer.emailService.connection import get_arq_connection_setting
from mailer.emailService.email_delivery_state import (
    is_email_already_sent,
    mark_email_as_failed,
    mark_email_as_retrying,
    mark_email_as_sent,
)
from mailer.emailService.email_models import EmailQueuePayload, EmailSchema
from mailer.emailService.email_retry_policy import calculate_email_retry_delay
from mailer.emailService.send_mail_service import PermanentEmailSendError, send_smtp_mail_function

EMAIL_ARQ_QUEUE_NAME = f"orbitrms:{EnvConfig.BACKEND_APP_ENVIRONMENT.lower()}:email:arq"


async def send_email_worker(ctx: dict, payload: dict) -> dict:

    queue_connection = ctx["redis"]
    email_job = EmailQueuePayload(**payload)
    job_try = int(ctx.get("job_try") or 1)

    if await is_email_already_sent(queue_connection, email_job.idempotency_key):
        return {
            "success": True,
            "skipped": True,
            "reason": "already_sent",
            "job_try": job_try,
        }

    try:
        email_data = EmailSchema(
            recipients_email=email_job.recipients_email,
            subject=email_job.subject,
            body=email_job.body,
            email_type=email_job.email_type,
            idempotency_key=email_job.idempotency_key,
            max_retries=email_job.max_retries,
            metadata=email_job.metadata,
        )

        provider_result = await send_smtp_mail_function(email_data, job_try=job_try)

        if not provider_result.get("success"):
            raise Exception(provider_result.get("error") or provider_result.get("message") or "Email sending failed")

        await mark_email_as_sent(queue_connection, email_job, provider_result, job_try)

        return {
            "success": True,
            "job_try": job_try,
            "provider_message_id": provider_result.get("provider_message_id"),
        }

    except PermanentEmailSendError as error:
        await mark_email_as_failed(queue_connection, email_job, job_try, error)
        raise

    except Exception as error:
        if job_try < email_job.max_retries:
            retry_delay = calculate_email_retry_delay(job_try)
            await mark_email_as_retrying(queue_connection, email_job, job_try, retry_delay, error)
            raise Retry(defer=retry_delay) from error

        await mark_email_as_failed(queue_connection, email_job, job_try, error)
        raise


async def startup(ctx):
    print(f"ARQ email worker started. queue={EMAIL_ARQ_QUEUE_NAME}")


async def shutdown(ctx):
    print("ARQ email worker stopped.")


class WorkerSettings:
    """Run with:

    arq mailer.emailService.worker.WorkerSettings
    """

    functions = [send_email_worker]
    redis_settings = get_arq_connection_setting()
    queue_name = EMAIL_ARQ_QUEUE_NAME
    max_jobs = 10
    job_timeout = 120
    max_tries = 5
    keep_result = 86400
    health_check_interval = 30
    on_startup = startup
    on_shutdown = shutdown
