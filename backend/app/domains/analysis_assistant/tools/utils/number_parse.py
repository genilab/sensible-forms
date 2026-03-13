from __future__ import annotations

import re
from typing import Any, Optional


_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def try_parse_float(value: Any) -> Optional[float]:
    """Best-effort parse of survey-ish numeric strings.

    Handles cases like:
    - "4", " 4 ", "4.2", "1,234"
    - "42%" (parsed as 42.0)
    - "4 - Agree" (parses leading 4)

    Returns None if parsing fails.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        # Reject NaNs implicitly by float conversion?
        try:
            return float(value)
        except Exception:
            return None

    s = str(value).strip()
    if not s:
        return None

    # Common cleanup
    s = s.replace(",", "")

    # If it contains a number anywhere, grab the first one
    m = _NUM_RE.search(s)
    if not m:
        return None

    try:
        return float(m.group(0))
    except Exception:
        return None
