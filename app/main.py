"""HTTP webhooks: inbound greeting, outbound TwiML, and status callbacks."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import VoiceResponse

from app.status_log import append_jsonl, build_status_record

load_dotenv()

app = FastAPI(title="twilio-jp-050-voice-bot")

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def validation_enabled() -> bool:
    mode = os.environ.get("TWILIO_VALIDATE_REQUESTS", "auto").strip().lower()
    if mode in _TRUE:
        return True
    if mode in _FALSE:
        return False
    return bool(os.environ.get("TWILIO_AUTH_TOKEN", "").strip())


def public_base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")


def signed_url(request: Request) -> str:
    url = f"{public_base_url()}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    return url


async def form_params(request: Request) -> dict[str, str]:
    cached = getattr(request.state, "form_params", None)
    if cached is not None:
        return cached
    form = await request.form()
    params: dict[str, str] = {}
    for key, value in form.multi_items():
        if hasattr(value, "filename"):
            continue
        params[str(key)] = str(value)
    request.state.form_params = params
    return params


async def guard(request: Request) -> Response | None:
    if not validation_enabled():
        return None
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if not token or not public_base_url():
        return Response(
            "Request validation is on, but TWILIO_AUTH_TOKEN or PUBLIC_BASE_URL is missing.\n",
            status_code=500,
            media_type="text/plain",
        )
    params = await form_params(request)
    signature = request.headers.get("X-Twilio-Signature", "")
    if not RequestValidator(token).validate(signed_url(request), params, signature):
        return Response(status_code=403)
    return None


def inbound_twiml() -> str:
    response = VoiceResponse()
    response.say(
        "こんにちは。こちらは Twilio の日本ゼロゴーゼロ番号の公開デモです。",
        language="ja-JP",
        voice="Polly.Mizuki",
    )
    response.say(
        "This is a public Twilio Japan 050 voice demo. Goodbye.",
        language="en-US",
        voice="Polly.Joanna",
    )
    response.hangup()
    return str(response)


def outbound_twiml() -> str:
    response = VoiceResponse()
    response.say(
        "こちらは Twilio の日本ゼロゴーゼロ番号からの発信テストです。",
        language="ja-JP",
        voice="Polly.Mizuki",
    )
    response.say(
        "This is an outbound test call from the Twilio Japan 050 demo. Goodbye.",
        language="en-US",
        voice="Polly.Joanna",
    )
    response.hangup()
    return str(response)


def xml_response(body: str) -> Response:
    return Response(content=body, media_type="text/xml")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "twilio-jp-050-voice-bot",
        "voice": "/voice",
        "outbound_twiml": "/outbound-twiml",
        "status": "/status",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/voice")
async def voice(request: Request) -> Response:
    rejected = await guard(request)
    if rejected is not None:
        return rejected
    return xml_response(inbound_twiml())


@app.post("/outbound-twiml")
async def outbound_voice(request: Request) -> Response:
    rejected = await guard(request)
    if rejected is not None:
        return rejected
    return xml_response(outbound_twiml())


@app.post("/status")
async def status(request: Request) -> Response:
    rejected = await guard(request)
    if rejected is not None:
        return rejected
    record = build_status_record(await form_params(request))
    path = os.environ.get("STATUS_LOG_PATH", "logs/call_status.jsonl").strip() or "logs/call_status.jsonl"
    append_jsonl(path, record)
    return Response(status_code=204)
