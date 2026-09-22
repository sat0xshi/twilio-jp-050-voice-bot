from app.masking import mask_phone, redact_phones


def test_masks_japan_050_and_keeps_last_four():
    masked = mask_phone("+815011112222")
    assert masked == "+81******2222"
    assert "1111" not in masked
    assert "815011112222" not in masked


def test_masks_other_e164_and_national_digits():
    assert mask_phone("+819012341234") == "+81******1234"
    assert mask_phone("05012345678") == "*******5678"
    assert "12345678" not in mask_phone("05012345678")


def test_non_numbers_do_not_pass_through():
    assert mask_phone(None) == ""
    assert mask_phone("") == ""
    assert mask_phone("abc") == "****"
    assert mask_phone("+81") == "****"


def test_redact_replaces_embedded_numbers():
    raw = "from=+815011112222"
    redacted = redact_phones(raw)
    assert "815011112222" not in redacted
    assert redacted == "from=+81******2222"
