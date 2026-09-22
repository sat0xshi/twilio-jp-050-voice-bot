import json

from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.main import app

TOKEN = "a" * 32
ORIGIN = "https://demo.example.net"


def test_health_and_root():
    client = TestClient(app)
    assert client.get("/health").json() == {"ok": True}
    body = client.get("/").json()
    assert body["voice"] == "/voice"
    assert body["status"] == "/status"


def test_voice_returns_bilingual_twiml_without_a_token():
    client = TestClient(app)
    response = client.post("/voice")
    assert response.status_code == 200
    assert "text/xml" in response.headers["content-type"]
    xml = response.text
    assert "こんにちは。こちらは Twilio の日本ゼロゴーゼロ番号の公開デモです。" in xml
    assert "This is a public Twilio Japan 050 voice demo. Goodbye." in xml
    assert 'language="ja-JP"' in xml
    assert 'language="en-US"' in xml
    assert "<Hangup" in xml


def test_outbound_twiml_is_distinct():
    client = TestClient(app)
    xml = client.post("/outbound-twiml").text
    assert "発信テスト" in xml
    assert "outbound test call" in xml


def test_status_writes_one_masked_jsonl_line(tmp_path, monkeypatch):
    log_path = tmp_path / "call_status.jsonl"
    monkeypatch.setenv("STATUS_LOG_PATH", str(log_path))
    monkeypatch.setenv("TWILIO_VALIDATE_REQUESTS", "false")
    client = TestClient(app)
    response = client.post(
        "/status",
        data={
            "CallSid": "CA0123456789abcdef0123456789abcdef",
            "CallStatus": "completed",
            "Direction": "inbound",
            "From": "+815011112222",
            "To": "+819012341234",
            "CallDuration": "8",
            "AccountSid": "AC_TEST_ACCOUNT",
        },
    )
    assert response.status_code == 204
    line = log_path.read_text(encoding="utf-8").strip()
    assert "815011112222" not in line
    assert "819012341234" not in line
    assert "AC_TEST_ACCOUNT" not in line
    record = json.loads(line)
    assert record["from"] == "+81******2222"
    assert record["to"] == "+81******1234"
    assert record["call_status"] == "completed"
    assert record["duration"] == "8"


def test_bad_signature_is_rejected_and_not_logged(tmp_path, monkeypatch):
    log_path = tmp_path / "call_status.jsonl"
    monkeypatch.setenv("STATUS_LOG_PATH", str(log_path))
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("TWILIO_VALIDATE_REQUESTS", "true")
    monkeypatch.setenv("PUBLIC_BASE_URL", ORIGIN)
    client = TestClient(app)
    response = client.post(
        "/status",
        data={"From": "+815011112222", "To": "+819012341234", "CallStatus": "ringing"},
        headers={"X-Twilio-Signature": "not-a-signature"},
    )
    assert response.status_code == 403
    assert not log_path.exists()


def test_valid_signature_allows_the_webhook(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("TWILIO_VALIDATE_REQUESTS", "true")
    monkeypatch.setenv("PUBLIC_BASE_URL", ORIGIN)
    params = {"CallSid": "CA123", "From": "+815011112222", "To": "+819012341234"}
    signature = RequestValidator(TOKEN).compute_signature(f"{ORIGIN}/voice", params)
    client = TestClient(app)
    response = client.post("/voice", data=params, headers={"X-Twilio-Signature": signature})
    assert response.status_code == 200
    assert "<Say" in response.text


def test_validation_requires_public_base_url(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("TWILIO_VALIDATE_REQUESTS", "true")
    client = TestClient(app)
    response = client.post("/voice", data={"CallSid": "CA123"})
    assert response.status_code == 500
    assert "PUBLIC_BASE_URL" in response.text
