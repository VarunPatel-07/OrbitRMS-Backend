import hashlib
import json
from typing import Any

from mailer.emailService.email_models import EmailSchema


#  We first  normalize the all the incoming recipient and make them in the list
def normalize_recipients(recipients: str | list[str]) -> list[str]:
    if isinstance(recipients, str):
        return [recipients.strip().lower()]
    return sorted(recipient.strip().lower() for recipient in recipients)


#  We will convert the text in the hash text
def hash_text_converter(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


#  Now We will stringify the json like we will convert all the incoming data in the string formate
def stringify_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def generate_email_idempotency_key(email_data: EmailSchema) -> str:
    if email_data.idempotency_key:
        return email_data.idempotency_key

    fingerprint = {
        "recipients": normalize_recipients(email_data.recipients_email),
        "subject": email_data.subject,
        "body_hash": hash_text_converter(email_data.body or ""),
        "email_type": email_data.email_type,
        "metadata": email_data.metadata,
    }

    digest = hash_text_converter(stringify_json(fingerprint))[:32]
    return f"email:{email_data.email_type}:{digest}"
