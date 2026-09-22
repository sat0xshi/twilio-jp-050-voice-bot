"""Mask phone numbers before they are written anywhere."""

from __future__ import annotations

import re

_DIGITS = re.compile(r"\d+")
_EMBEDDED_E164 = re.compile(r"\+[1-9]\d{7,14}")


def mask_phone(value: object) -> str:
    """Keep a short prefix and the last four digits. Drop the rest.

    ``+815012345678`` becomes ``+81******5678``. Values that are not phone
    numbers become ``****`` so a log line never keeps the raw input.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    digits = "".join(_DIGITS.findall(text))
    if len(digits) < 4:
        return "****"
    last4 = digits[-4:]
    if text.startswith("+"):
        prefix_len = 2 if len(digits) > 6 else 1
        hidden = max(len(digits) - prefix_len - 4, 2)
        return f"+{digits[:prefix_len]}{'*' * hidden}{last4}"
    return f"{'*' * max(len(digits) - 4, 4)}{last4}"


def redact_phones(text: str) -> str:
    """Replace any E.164 number embedded in ``text``."""
    return _EMBEDDED_E164.sub(lambda match: mask_phone(match.group(0)), text)
