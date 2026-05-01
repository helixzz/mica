"""Tests for feishu webhook URL verification and approval callback parsing."""


def test_webhook_url_verification():
    from app.services.feishu.webhooks import parse_url_verification

    body = {"type": "url_verification", "challenge": "test-challenge"}
    challenge = parse_url_verification(body)
    assert challenge == "test-challenge"


def test_webhook_no_challenge_for_non_verification():
    from app.services.feishu.webhooks import parse_url_verification

    body = {"type": "event_callback", "event": {}}
    challenge = parse_url_verification(body)
    assert challenge is None


def test_webhook_approval_parsing():
    from app.services.feishu.webhooks import parse_approval_callback

    body = {
        "event": {
            "type": "approval_instance",
            "approval_code": "7C6F21E4-B912-C4A1-4567-ECF456D0F98A",
            "instance_code": "ABC-123",
            "status": "APPROVED",
        }
    }
    parsed = parse_approval_callback(body)
    assert parsed["status"] == "APPROVED"
    assert parsed["instance_id"] == "ABC-123"


def test_webhook_approval_parsing_rejected():
    from app.services.feishu.webhooks import parse_approval_callback

    body = {
        "event": {
            "type": "approval_instance",
            "approval_code": "code",
            "instance_code": "XYZ",
            "status": "REJECTED",
        }
    }
    parsed = parse_approval_callback(body)
    assert parsed["status"] == "REJECTED"


def test_webhook_non_approval_events_ignored():
    from app.services.feishu.webhooks import parse_approval_callback

    body = {"event": {"type": "message", "text": "hello"}}
    parsed = parse_approval_callback(body)
    assert parsed is None
