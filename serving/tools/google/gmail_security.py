from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any


CONFIRM_SECRET = os.getenv("GMAIL_CONFIRM_SECRET", "local-dev-secret-change-me")
CONFIRM_TTL_SEC = int(os.getenv("GMAIL_CONFIRM_TTL_SEC", "600"))


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_confirmation_token(*, action: str, payload: dict[str, Any]) -> str:
    body = {
        "action": action,
        "payload": payload,
        "issued_at": int(time.time()),
    }
    raw = _canonical(body)
    sig = hmac.new(CONFIRM_SECRET.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return json.dumps({"body": body, "sig": sig}, ensure_ascii=False, sort_keys=True)


def verify_confirmation_token(*, token: str, action: str, payload: dict[str, Any]) -> bool:
    try:
        parsed = json.loads(token)
        body = parsed["body"]
        sig = parsed["sig"]
    except Exception:
        return False

    if body.get("action") != action:
        return False
    if body.get("payload") != payload:
        return False

    issued_at = int(body.get("issued_at", 0))
    if time.time() - issued_at > CONFIRM_TTL_SEC:
        return False

    expected = hmac.new(
        CONFIRM_SECRET.encode("utf-8"),
        _canonical(body).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


def require_confirmation(*, action: str, payload: dict[str, Any], confirmation_token: str | None) -> None:
    if not confirmation_token:
        raise PermissionError(
            f"{action} requires explicit user confirmation. First call the matching propose_* tool, "
            "show the proposed action to the user, then call this tool with the returned confirmation_token only after the user confirms."
        )
    if not verify_confirmation_token(token=confirmation_token, action=action, payload=payload):
        raise PermissionError("Invalid or expired Gmail confirmation token.")
