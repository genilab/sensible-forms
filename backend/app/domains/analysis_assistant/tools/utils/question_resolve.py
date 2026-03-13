from __future__ import annotations

import re
from typing import Iterable, Optional


_DIGITS_RE = re.compile(r"(\d+)")


def _extract_digits(s: str) -> Optional[str]:
    m = _DIGITS_RE.search(s)
    return m.group(1) if m else None


def resolve_question_id(*, user_ref: str, known_ids: Iterable[str]) -> str:
    """Resolve a user-provided question reference to a known question id.

    Design goal: avoid overfitting.

    - If user_ref exactly matches a known id, return it.
    - Otherwise, attempt *conservative* resolution for inputs like "question 3", "q3", "#3":
      match against known ids by numeric component *only if* the match is unambiguous.
    - If ambiguous or no match, return user_ref unchanged.
    """

    ref = str(user_ref).strip()
    if not ref:
        return ref

    known_list = [str(k) for k in known_ids if k is not None]
    known_set = set(known_list)

    # Exact match wins.
    if ref in known_set:
        return ref

    # Case-insensitive exact match.
    ref_l = ref.lower()
    ci_matches = [k for k in known_list if k.lower() == ref_l]
    if len(ci_matches) == 1:
        return ci_matches[0]

    # Conservative numeric resolution.
    digits = _extract_digits(ref_l)
    if not digits:
        return ref

    digit_matches = [k for k in known_list if _extract_digits(k.lower()) == digits]
    if len(digit_matches) == 1:
        return digit_matches[0]

    # Prefer common short forms if present among ambiguous matches.
    if digit_matches:
        preferred = [k for k in digit_matches if k.lower() in {f"q{digits}", f"question {digits}", digits}]
        if len(preferred) == 1:
            return preferred[0]

    return ref
