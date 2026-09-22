"""Append one JSON object per call-status callback."""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from app.masking import mask_phone, redact_phones

_LOCK = threading.Lock()


def build_status_record(
    params: Mapping[str, str],
    *,
    now: datetime | None = None,
) -> dict[str, str]:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return {
        "ts": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "call_sid": params.get("CallSid", ""),
        "call_status": params.get("CallStatus", ""),
        "direction": params.get("Direction", ""),
        "from": mask_phone(params.get("From")),
        "to": mask_phone(params.get("To")),
        "duration": params.get("CallDuration") or params.get("Duration") or "",
    }


def append_jsonl(path: str | Path, record: Mapping[str, str]) -> None:
    safe = {str(key): redact_phones("" if value is None else str(value)) for key, value in record.items()}
    line = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with dest.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
