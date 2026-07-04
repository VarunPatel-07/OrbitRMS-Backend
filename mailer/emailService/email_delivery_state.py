import json
import time

from config.EnvConfig import EnvConfig
from mailer.emailService.email_models import EmailQueuePayload


# Now We will have the email state key in which we will generate the key based on the environment and the idempotency_key
def email_state_key(status: str, idempotency_key: str) -> str:

    env = EnvConfig.BACKEND_APP_ENVIRONMENT.lower()

    return f"orbitrms:{env}:email:{status}:{idempotency_key}"


async def is_email_already_sent(redis, idempotency_key: str) -> bool:
    return bool(await redis.exists(email_state_key("sent", idempotency_key)))


#  Now We will have the three function in which we will have the three function like mark email as sent, mark mail as retry, mark mail as failed
async def mark_email_as_sent(queue_connection, payload: EmailQueuePayload, provider_result: dict, job_try: int) -> None:

    record = {
        "idempotency_key": payload.idempotency_key,
        "email_type": payload.email_type,
        "recipient_count": payload.recipient_count,
        "subject": payload.subject,
        "provider_message_id": provider_result.get("provider_message_id"),
        "job_try": job_try,
        "sent_at": int(time.time()),
    }

    return await queue_connection.set(
        email_state_key("sent", payload.idempotency_key),
        json.dumps(record, sort_keys=True),
        ex=7 * 24 * 3600,
    )


async def mark_email_as_retrying(
    queue_connection,
    payload: EmailQueuePayload,
    job_try: int,
    next_retry_in_seconds: int,
    error: Exception,
) -> None:

    record = {
        "idempotency_key": payload.idempotency_key,
        "email_type": payload.email_type,
        "recipient_count": payload.recipient_count,
        "subject": payload.subject,
        "attempt": job_try,
        "next_retry_in_seconds": next_retry_in_seconds,
        "last_error": str(error),
        "updated_at": int(time.time()),
    }

    return await queue_connection.set(
        email_state_key("retrying", payload.idempotency_key),
        json.dumps(record, sort_keys=True),
        ex=24 * 3600,
    )


async def mark_email_as_failed(
    queue_connection,
    payload: EmailQueuePayload,
    job_try: int,
    error: Exception,
) -> None:

    record = {
        "idempotency_key": payload.idempotency_key,
        "email_type": payload.email_type,
        "recipient_count": payload.recipient_count,
        "subject": payload.subject,
        "max_retries": payload.max_retries,
        "final_attempt": job_try,
        "last_error": str(error),
        "failed_at": int(time.time()),
        "metadata": payload.metadata,
    }

    return await queue_connection.set(
        email_state_key("failed", payload.idempotency_key),
        json.dumps(record, sort_keys=True),
        ex=7 * 24 * 3600,
    )
