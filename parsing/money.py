"""Helpers for the comma-decimal money strings used on Lidl receipts.

Receipts print amounts as "1,32"; this module converts between that form and
floats in one place so the parsers don't each reinvent it.
"""

from typing import Any, Optional


def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Parse a receipt money/quantity string ("1,32" or "1.32") into a float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except (ValueError, AttributeError):
        return default


def to_str(value: Optional[float]) -> Optional[str]:
    """Format a float back into the receipt's comma-decimal form ("1,32")."""
    if value is None:
        return None
    return f"{value:.2f}".replace(".", ",")
