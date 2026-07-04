import time
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class EmailSchema(BaseModel):
    recipients_email: str | List[str]
    subject: str
    body: Optional[str] = None
    email_type: str = "generic"
    idempotency_key: Optional[str] = None
    max_retries: int = 5
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("recipients_email")
    @classmethod
    def validate_recipients_email_field(cls, value: str | List[str]):
        recipients = [value] if isinstance(value, str) else value

        normalize_recipients = [
            recipient.strip().lower() for recipient in recipients if recipient and recipient.strip()
        ]

        if not normalize_recipients:
            raise ValueError("at least one recipient is required")

        return normalize_recipients[0] if isinstance(value, str) else normalize_recipients

    @field_validator("subject")
    @classmethod
    def validate_subject_field(cls, value: str):
        normalize_field = value.strip()

        if not normalize_field:
            raise ValueError("subject is required")

        return normalize_field

    @field_validator("max_retries")
    @classmethod
    def validate_subject_field(cls, value: int):
        if value < 1:
            raise ValueError("max_retries must be at least 1")

        return value


class EmailQueuePayload(BaseModel):
    recipients_email: str | List[str]
    subject: str
    body: Optional[str] = None
    email_type: str = "generic"
    idempotency_key: str
    max_retries: int = 5
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default_factory=lambda: int(time.time()))

    @property
    def recipient_count(self) -> int:
        return 1 if isinstance(self.recipients_email, str) else len(self.recipients_email)
