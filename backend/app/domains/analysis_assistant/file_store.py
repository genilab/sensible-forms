from __future__ import annotations

"""In-memory file store for the Analysis Assistant domain.

This module is a tiny, process-local storage layer used to hold uploaded CSV bytes
between requests.

Key properties:
- Ephemeral: data is kept in memory only (lost on process restart)
- Process-local: not shared across multiple worker processes
- TTL-based eviction: old entries are purged on access
"""

import time
from dataclasses import dataclass
from uuid import uuid4


DEFAULT_TTL_SECONDS = 1800  # 30 minutes


@dataclass
class _StoredFile:
    """Internal record for a stored upload."""

    data: bytes
    filename: str
    created_at: float
    last_access_at: float


# Shared store across imports/instances.
# Note: in multi-worker deployments each worker has its own in-memory store.
_STORE: dict[str, _StoredFile] = {}


def _now() -> float:
    return time.time()


def _purge_expired(*, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    """Evict entries that haven't been accessed within `ttl_seconds`.

    We purge opportunistically on store operations.
    """

    cutoff = _now() - float(ttl_seconds)

    # Avoid mutating the dict while iterating over it.
    expired_keys: list[str] = []
    for file_id, stored in _STORE.items():
        if stored.last_access_at < cutoff:
            expired_keys.append(file_id)

    for k in expired_keys:
        _STORE.pop(k, None)


def save_file(file_bytes: bytes, *, filename: str) -> str:
    """Persist uploaded bytes and return an opaque `file_id`."""

    _purge_expired()

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    file_id = str(uuid4())
    ts = _now()
    _STORE[file_id] = _StoredFile(
        data=file_bytes,
        filename=filename,
        created_at=ts,
        last_access_at=ts,
    )

    return file_id


def load_file(file_id_or_name: str) -> bytes:
    """Load stored bytes by `file_id`.

    The parameter name is `file_id_or_name` for legacy reasons; currently the store
    is keyed by UUID `file_id` values returned from `save_file()`.
    """

    _purge_expired()

    try:
        stored = _STORE[file_id_or_name]
        # Touch the record so it stays alive.
        stored.last_access_at = _now()
        return stored.data
    except KeyError as e:
        raise FileNotFoundError(f"No such stored file: {file_id_or_name}") from e


def get_original_filename(file_id: str) -> str | None:
    """Return the client-provided filename for display/debugging."""

    _purge_expired()
    stored = _STORE.get(file_id)
    return stored.filename if stored else None


def delete_file(file_id: str) -> None:
    """Best-effort deletion (no error if missing)."""

    _STORE.pop(file_id, None)
