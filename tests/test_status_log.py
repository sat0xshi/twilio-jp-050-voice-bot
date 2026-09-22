import json
from datetime import datetime, timezone

from app.status_log import append_jsonl, build_status_record


def test_record_masks_both_parties_and_drops_account_sid():
    record = build_status_record(
        {
            "CallSid": "CA0123456789abcdef0123456789abcdef",
            "CallStatus": "completed",
            "Direction": "inbound",
            "From": "+815011112222",
            "To": "+819012341234",
            "CallDuration": "8",
            "AccountSid": "AC_TEST_ACCOUNT",
        },
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert record == {
        "ts": "2026-01-01T00:00:00Z",
        "call_sid": "CA0123456789abcdef0123456789abcdef",
        "call_status": "completed",
        "direction": "inbound",
        "from": "+81******2222",
        "to": "+81******1234",
        "duration": "8",
    }
    blob = json.dumps(record)
    assert "815011112222" not in blob
    assert "819012341234" not in blob
    assert "AccountSid" not in blob


def test_append_scrubs_a_raw_number_that_slips_into_a_field(tmp_path):
    path = tmp_path / "call_status.jsonl"
    append_jsonl(path, {"call_status": "failed +815011112222"})
    text = path.read_text(encoding="utf-8")
    assert "815011112222" not in text
    assert "+81******2222" in text
    json.loads(text)
