import random

EMAIL_RETRY_DELAYS_SECONDS = [60, 120, 300, 600, 900]


def calculate_email_retry_delay(job_try: int, jitter_seconds: int = 15) -> int:

    safe_try = max(int(job_try), 1)
    base_delay = EMAIL_RETRY_DELAYS_SECONDS[min(safe_try - 1, len(EMAIL_RETRY_DELAYS_SECONDS) - 1)]

    if jitter_seconds <= 0:
        return base_delay

    return base_delay + random.randint(0, jitter_seconds)
