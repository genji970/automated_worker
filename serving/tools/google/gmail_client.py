from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError

from serving.tools.google.gmail_auth import get_gmail_service


DEFAULT_TIMEZONE = "Asia/Seoul"
MAX_BODY_CHARS = 12000


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {h.get("name", "").lower(): h.get("value", "") for h in headers if h.get("name")}


def _decode_base64url(data: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return raw.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_text(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain":
        return _decode_base64url(body_data)
    if mime_type == "text/html":
        return _html_to_text(_decode_base64url(body_data))

    plain: list[str] = []
    html: list[str] = []
    for part in payload.get("parts", []) or []:
        text = _extract_text(part)
        if not text:
            continue
        if part.get("mimeType") == "text/html":
            html.append(text)
        else:
            plain.append(text)

    return "\n\n".join(plain or html).strip()


def _normalize_date(date_value: str) -> str:
    if not date_value:
        return ""
    try:
        return parsedate_to_datetime(date_value).isoformat()
    except Exception:
        return date_value


def _summary_from_message(msg: dict[str, Any]) -> dict[str, Any]:
    headers = _headers_to_dict(msg.get("payload", {}).get("headers", []) or [])
    return {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "label_ids": msg.get("labelIds", []),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": _normalize_date(headers.get("date", "")),
        "snippet": msg.get("snippet", ""),
        "internal_date": msg.get("internalDate"),
    }


def build_date_query(
    *,
    date_preset: str | None = None,
    after: str | None = None,
    before: str | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    exclude_spam: bool = True,
    exclude_trash: bool = True,
    extra_query: str | None = None,
    unread_only: bool = False,
) -> str:
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()

    if date_preset == "today":
        start = today
        end = today + timedelta(days=1)
    elif date_preset == "yesterday":
        start = today - timedelta(days=1)
        end = today
    elif date_preset == "last_7_days":
        start = today - timedelta(days=7)
        end = today + timedelta(days=1)
    else:
        start = datetime.strptime(after, "%Y-%m-%d").date() if after else None
        end = datetime.strptime(before, "%Y-%m-%d").date() if before else None

    parts: list[str] = []
    if start:
        parts.append(f"after:{start.strftime('%Y/%m/%d')}")
    if end:
        parts.append(f"before:{end.strftime('%Y/%m/%d')}")
    if unread_only:
        parts.append("is:unread")
    if exclude_spam:
        parts.append("-in:spam")
    if exclude_trash:
        parts.append("-in:trash")
    if extra_query:
        parts.append(f"({extra_query})")
    return " ".join(parts).strip()


def list_labels() -> dict[str, Any]:
    service = get_gmail_service()
    response = service.users().labels().list(userId="me").execute()
    labels = response.get("labels", []) or []
    return {"count": len(labels), "labels": labels}


def search_messages(*, query: str, max_results: int = 20) -> dict[str, Any]:
    service = get_gmail_service()
    max_results = max(1, min(int(max_results), 100))

    try:
        response = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    except HttpError as exc:
        raise RuntimeError(f"Gmail search failed: {exc}") from exc

    messages = []
    for item in response.get("messages", []) or []:
        msg = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        messages.append(_summary_from_message(msg))

    return {
        "query": query,
        "count": len(messages),
        "messages": messages,
        "next_page_token": response.get("nextPageToken"),
    }


def read_messages(*, message_ids: list[str], include_body: bool = True, limit: int = 10) -> dict[str, Any]:
    service = get_gmail_service()
    safe_ids = [str(x) for x in message_ids][: max(1, min(int(limit), 50))]
    results = []

    for message_id in safe_ids:
        msg = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full" if include_body else "metadata",
        ).execute()
        item = _summary_from_message(msg)
        if include_body:
            body = _extract_text(msg.get("payload", {}))
            item["body_text"] = body[:MAX_BODY_CHARS]
            item["body_truncated"] = len(body) > MAX_BODY_CHARS
        results.append(item)

    return {"count": len(results), "messages": results}


def modify_messages(
    *,
    message_ids: list[str],
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> dict[str, Any]:
    service = get_gmail_service()
    safe_ids = [str(x) for x in message_ids][:1000]
    if not safe_ids:
        return {"count": 0, "modified": []}
    body = {
        "ids": safe_ids,
        "addLabelIds": add_label_ids or [],
        "removeLabelIds": remove_label_ids or [],
    }
    service.users().messages().batchModify(userId="me", body=body).execute()
    return {
        "count": len(safe_ids),
        "modified": safe_ids,
        "add_label_ids": add_label_ids or [],
        "remove_label_ids": remove_label_ids or [],
    }


def archive_messages(*, message_ids: list[str]) -> dict[str, Any]:
    return modify_messages(message_ids=message_ids, remove_label_ids=["INBOX"])


def mark_messages_read(*, message_ids: list[str]) -> dict[str, Any]:
    return modify_messages(message_ids=message_ids, remove_label_ids=["UNREAD"])


def mark_messages_unread(*, message_ids: list[str]) -> dict[str, Any]:
    return modify_messages(message_ids=message_ids, add_label_ids=["UNREAD"])


def trash_messages(*, message_ids: list[str]) -> dict[str, Any]:
    service = get_gmail_service()
    safe_ids = [str(x) for x in message_ids][:100]
    trashed = []
    for message_id in safe_ids:
        service.users().messages().trash(userId="me", id=message_id).execute()
        trashed.append(message_id)
    return {"count": len(trashed), "trashed": trashed}


def create_draft(
    *,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    reply_message_id: str | None = None,
) -> dict[str, Any]:
    service = get_gmail_service()
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    draft_body: dict[str, Any] = {"message": {"raw": raw}}

    if reply_message_id:
        original = service.users().messages().get(userId="me", id=reply_message_id, format="metadata").execute()
        draft_body["message"]["threadId"] = original.get("threadId")

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return {"draft_id": draft.get("id"), "message": draft.get("message", {})}


def send_draft(*, draft_id: str) -> dict[str, Any]:
    service = get_gmail_service()
    sent = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    return {"sent_message_id": sent.get("id"), "thread_id": sent.get("threadId")}
