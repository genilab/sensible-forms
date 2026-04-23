from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


def redact_text(text: str) -> str:
    text = _EMAIL_RE.sub("<redacted_email>", text)
    text = _PHONE_RE.sub("<redacted_phone>", text)
    return text
