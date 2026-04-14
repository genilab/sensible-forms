from __future__ import annotations

"""In-memory file store for the Analysis Assistant domain.

- This is process-local and ephemeral.
"""

import time
from dataclasses import dataclass
from uuid import uuid4


DEFAULT_TTL_SECONDS = 1800  # 30 minutes


@dataclass
class _StoredFile:
    data: bytes
    filename: str
    created_at: float
    last_access_at: float


# Shared store across imports/instances.
_STORE: dict[str, _StoredFile] = {}


def _now() -> float:
    return time.time()


def _purge_expired(*, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    cutoff = _now() - float(ttl_seconds)
    expired_keys: list[str] = []
    for file_id, stored in _STORE.items():
        if stored.last_access_at < cutoff:
            expired_keys.append(file_id)
    for k in expired_keys:
        _STORE.pop(k, None)


def save_file(file_bytes: bytes, *, filename: str) -> str:
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
    _purge_expired()
    try:
        stored = _STORE[file_id_or_name]
        stored.last_access_at = _now()
        return stored.data
    except KeyError as e:
        raise FileNotFoundError(f"No such stored file: {file_id_or_name}") from e


def get_original_filename(file_id: str) -> str | None:
    _purge_expired()
    stored = _STORE.get(file_id)
    return stored.filename if stored else None


def delete_file(file_id: str) -> None:
    """Best-effort deletion (no error if missing)."""
    _STORE.pop(file_id, None)
