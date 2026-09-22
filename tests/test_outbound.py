import pytest

from app.outbound import load_config, main, place_call

SID = "AC" + "ab" * 16
TOKEN = "cd" * 16
FROM_050 = "+815012340000"
TO = "+819012340000"
ORIGIN = "https://demo.example.net"


def _env(monkeypatch, **overrides):
    values = {
        "TWILIO_ACCOUNT_SID": SID,
        "TWILIO_AUTH_TOKEN": TOKEN,
        "TWILIO_FROM_NUMBER": FROM_050,
        "OUTBOUND_TO": TO,
        "PUBLIC_BASE_URL": ORIGIN,
    }
    values.update(overrides)
    for key, value in values.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def test_load_config_rejects_missing_and_placeholder_values(monkeypatch):
    with pytest.raises(ValueError, match="Missing env"):
        load_config()

    _env(monkeypatch, TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    with pytest.raises(ValueError, match="TWILIO_ACCOUNT_SID"):
        load_config()

    _env(monkeypatch, TWILIO_FROM_NUMBER="+14155552671")
    with pytest.raises(ValueError, match="050"):
        load_config()

    _env(monkeypatch, PUBLIC_BASE_URL="https://demo.example.net/voice")
    with pytest.raises(ValueError, match="origin only"):
        load_config()


def test_place_call_uses_the_env_destination_and_status_callback(monkeypatch):
    _env(monkeypatch)
    created = {}

    class FakeCall:
        sid = "CA0123456789abcdef0123456789abcdef"
        status = "queued"

    class FakeCalls:
        def create(self, **kwargs):
            created.update(kwargs)
            return FakeCall()

    class FakeClient:
        def __init__(self, account_sid, auth_token):
            assert account_sid == SID
            assert auth_token == TOKEN
            self.calls = FakeCalls()

    monkeypatch.setattr("app.outbound.Client", FakeClient)
    call = place_call()
    assert call.sid == "CA0123456789abcdef0123456789abcdef"
    assert created["to"] == TO
    assert created["from_"] == FROM_050
    assert created["url"] == f"{ORIGIN}/outbound-twiml"
    assert created["status_callback"] == f"{ORIGIN}/status"
    assert created["method"] == "POST"
    assert created["status_callback_method"] == "POST"
    assert created["status_callback_event"] == ["initiated", "ringing", "answered", "completed"]
    assert created["time_limit"] == 30


def test_main_prints_masked_numbers_and_hides_twilio_errors(monkeypatch, capsys):
    _env(monkeypatch)

    class FakeCall:
        sid = "CA0123456789abcdef0123456789abcdef"
        status = "queued"

    class FakeCalls:
        def create(self, **kwargs):
            return FakeCall()

    class FakeClient:
        def __init__(self, account_sid, auth_token):
            self.calls = FakeCalls()

    monkeypatch.setattr("app.outbound.Client", FakeClient)
    assert main() == 0
    out = capsys.readouterr().out
    assert "call_sid=CA0123456789abcdef0123456789abcdef" in out
    assert TO not in out
    assert FROM_050 not in out
    assert "+81******0000" in out

    class BoomClient:
        def __init__(self, account_sid, auth_token):
            self.calls = self

        def create(self, **kwargs):
            from twilio.base.exceptions import TwilioRestException

            raise TwilioRestException(
                status=400,
                uri="/Calls",
                msg=f"to {TO} is unverified",
                code=21219,
            )

    monkeypatch.setattr("app.outbound.Client", BoomClient)
    assert main() == 1
    err = capsys.readouterr().err
    assert "http_status=400" in err
    assert "21219" in err
    assert TO not in err
    assert TOKEN not in err
