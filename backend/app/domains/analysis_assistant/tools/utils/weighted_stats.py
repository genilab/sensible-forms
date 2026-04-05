from __future__ import annotations

from typing import Iterable


def weighted_mean(pairs: Iterable[tuple[float, float]], *, zero_fallback: float = 0.0) -> float:
    """Compute a weighted mean for (value, weight) pairs.

    If the total weight is <= 0, returns ``zero_fallback``.
    """

    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return zero_fallback
    return sum(x * w for x, w in pairs) / total_w


def weighted_variance(
    pairs: Iterable[tuple[float, float]],
    mean: float,
    *,
    zero_fallback: float = 0.0,
) -> float:
    """Compute a weighted population variance for (value, weight) pairs.

    If the total weight is <= 0, returns ``zero_fallback``.
    """

    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return zero_fallback
    return sum(w * (x - mean) ** 2 for x, w in pairs) / total_w


__all__ = ["weighted_mean", "weighted_variance"]
