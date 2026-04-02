from __future__ import annotations

import os
import sys
from pathlib import Path


# Keep tests deterministic even when developers have real API keys in their
# environment. Force mock LLM provider for the entire test session.
os.environ["LLM_PROVIDER"] = "mock"


def _ensure_backend_on_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    backend_dir = repo_root / "backend"
    backend_dir_str = str(backend_dir)
    if backend_dir_str not in sys.path:
        sys.path.insert(0, backend_dir_str)


_ensure_backend_on_syspath()
