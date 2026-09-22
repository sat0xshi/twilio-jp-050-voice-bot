import pytest

_ENV_KEYS = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "OUTBOUND_TO",
    "PUBLIC_BASE_URL",
    "TWILIO_VALIDATE_REQUESTS",
    "STATUS_LOG_PATH",
    "HOST",
    "PORT",
    "BOT_NAME",
)


@pytest.fixture(autouse=True)
def clear_twilio_env(monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
