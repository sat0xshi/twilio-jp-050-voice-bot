"""Place one outbound call from the Japan 050 number."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.masking import mask_phone

_ACCOUNT_SID = re.compile(r"^AC[0-9a-fA-F]{32}$")
_AUTH_TOKEN = re.compile(r"^[0-9a-fA-F]{32}$")
_FROM_050 = re.compile(r"^\+8150\d{8}$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

_REQUIRED = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "OUTBOUND_TO",
    "PUBLIC_BASE_URL",
)


def load_config() -> dict[str, str]:
    values = {name: os.environ.get(name, "").strip() for name in _REQUIRED}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ValueError(
            "Missing env: " + ", ".join(missing) + ". Copy .env.example to .env and fill it in."
        )

    if not _ACCOUNT_SID.match(values["TWILIO_ACCOUNT_SID"]):
        raise ValueError("TWILIO_ACCOUNT_SID must be AC followed by 32 hex characters.")
    if not _AUTH_TOKEN.match(values["TWILIO_AUTH_TOKEN"]):
        raise ValueError("TWILIO_AUTH_TOKEN must be the 32-character Auth Token from the Twilio console.")
    if not _FROM_050.match(values["TWILIO_FROM_NUMBER"]):
        raise ValueError(
            "TWILIO_FROM_NUMBER must be the Japan 050 number in E.164 (+8150 and 8 digits). "
            f"Got {mask_phone(values['TWILIO_FROM_NUMBER'])}."
        )
    if not _E164.match(values["OUTBOUND_TO"]):
        raise ValueError(
            "OUTBOUND_TO must be an E.164 destination. "
            f"Got {mask_phone(values['OUTBOUND_TO'])}."
        )

    base = values["PUBLIC_BASE_URL"].rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("PUBLIC_BASE_URL must be an absolute http(s) origin.")
    if parsed.username or parsed.password:
        raise ValueError("PUBLIC_BASE_URL must not include a username or password.")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("PUBLIC_BASE_URL must be the origin only, with no path or query.")
    values["PUBLIC_BASE_URL"] = base
    return values


def place_call(config: dict[str, str] | None = None, client: Client | None = None):
    cfg = config if config is not None else load_config()
    twilio = client or Client(cfg["TWILIO_ACCOUNT_SID"], cfg["TWILIO_AUTH_TOKEN"])
    base = cfg["PUBLIC_BASE_URL"]
    return twilio.calls.create(
        to=cfg["OUTBOUND_TO"],
        from_=cfg["TWILIO_FROM_NUMBER"],
        url=f"{base}/outbound-twiml",
        method="POST",
        status_callback=f"{base}/status",
        status_callback_method="POST",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        timeout=20,
        time_limit=30,
    )


def main() -> int:
    load_dotenv()
    try:
        cfg = load_config()
        call = place_call(cfg)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except TwilioRestException as exc:
        print(
            f"Twilio request failed: http_status={exc.status} code={exc.code}",
            file=sys.stderr,
        )
        return 1
    print(
        f"call_sid={call.sid} status={call.status} "
        f"to={mask_phone(cfg['OUTBOUND_TO'])} from={mask_phone(cfg['TWILIO_FROM_NUMBER'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
