from __future__ import annotations

from typing import Any

from serving.tools.google.gmail_client import (
    archive_messages,
    build_date_query,
    create_draft,
    list_labels,
    mark_messages_read,
    mark_messages_unread,
    modify_messages,
    read_messages,
    search_messages,
    send_draft,
    trash_messages,
)
from serving.tools.google.gmail_security import make_confirmation_token, require_confirmation


def gmail_list_labels() -> dict[str, Any]:
    return list_labels()


def gmail_search_messages(
    *,
    query: str | None = None,
    date_preset: str | None = None,
    after: str | None = None,
    before: str | None = None,
    exclude_spam: bool = True,
    exclude_trash: bool = True,
    extra_query: str | None = None,
    unread_only: bool = False,
    max_results: int = 20,
) -> dict[str, Any]:
    if not query:
        query = build_date_query(
            date_preset=date_preset,
            after=after,
            before=before,
            exclude_spam=exclude_spam,
            exclude_trash=exclude_trash,
            extra_query=extra_query,
            unread_only=unread_only,
        )
    if not query:
        raise ValueError("Either query, date_preset, or date range must be provided.")
    return search_messages(query=query, max_results=max_results)


def gmail_read_messages(
    *,
    message_ids: list[str],
    include_body: bool = True,
    limit: int = 10,
) -> dict[str, Any]:
    return read_messages(message_ids=message_ids, include_body=include_body, limit=limit)


def gmail_propose_archive_messages(*, message_ids: list[str]) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    return {
        "requires_confirmation": True,
        "action": "gmail_archive_messages",
        "payload": payload,
        "confirmation_token": make_confirmation_token(action="gmail_archive_messages", payload=payload),
        "message": "Ask the user to confirm before archiving these emails.",
    }


def gmail_archive_messages(*, message_ids: list[str], confirmation_token: str | None = None) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    require_confirmation(action="gmail_archive_messages", payload=payload, confirmation_token=confirmation_token)
    return archive_messages(message_ids=message_ids)


def gmail_propose_apply_label(
    *,
    message_ids: list[str],
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "message_ids": message_ids,
        "add_label_ids": add_label_ids or [],
        "remove_label_ids": remove_label_ids or [],
    }
    return {
        "requires_confirmation": True,
        "action": "gmail_apply_label",
        "payload": payload,
        "confirmation_token": make_confirmation_token(action="gmail_apply_label", payload=payload),
        "message": "Ask the user to confirm before changing labels on these emails.",
    }


def gmail_apply_label(
    *,
    message_ids: list[str],
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
    confirmation_token: str | None = None,
) -> dict[str, Any]:
    payload = {
        "message_ids": message_ids,
        "add_label_ids": add_label_ids or [],
        "remove_label_ids": remove_label_ids or [],
    }
    require_confirmation(action="gmail_apply_label", payload=payload, confirmation_token=confirmation_token)
    return modify_messages(message_ids=message_ids, add_label_ids=add_label_ids, remove_label_ids=remove_label_ids)


def gmail_propose_trash_messages(*, message_ids: list[str]) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    return {
        "requires_confirmation": True,
        "action": "gmail_trash_messages",
        "payload": payload,
        "confirmation_token": make_confirmation_token(action="gmail_trash_messages", payload=payload),
        "message": "Ask the user to confirm before moving these emails to trash.",
    }


def gmail_trash_messages(*, message_ids: list[str], confirmation_token: str | None = None) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    require_confirmation(action="gmail_trash_messages", payload=payload, confirmation_token=confirmation_token)
    return trash_messages(message_ids=message_ids)


def gmail_propose_mark_read(*, message_ids: list[str]) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    return {
        "requires_confirmation": True,
        "action": "gmail_mark_read",
        "payload": payload,
        "confirmation_token": make_confirmation_token(action="gmail_mark_read", payload=payload),
        "message": "Ask the user to confirm before marking these emails as read.",
    }


def gmail_mark_read(*, message_ids: list[str], confirmation_token: str | None = None) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    require_confirmation(action="gmail_mark_read", payload=payload, confirmation_token=confirmation_token)
    return mark_messages_read(message_ids=message_ids)


def gmail_propose_mark_unread(*, message_ids: list[str]) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    return {
        "requires_confirmation": True,
        "action": "gmail_mark_unread",
        "payload": payload,
        "confirmation_token": make_confirmation_token(action="gmail_mark_unread", payload=payload),
        "message": "Ask the user to confirm before marking these emails as unread.",
    }


def gmail_mark_unread(*, message_ids: list[str], confirmation_token: str | None = None) -> dict[str, Any]:
    payload = {"message_ids": message_ids}
    require_confirmation(action="gmail_mark_unread", payload=payload, confirmation_token=confirmation_token)
    return mark_messages_unread(message_ids=message_ids)


def gmail_create_draft(
    *,
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    reply_message_id: str | None = None,
) -> dict[str, Any]:
    # Draft creation is allowed without confirmation because it does not send email.
    return create_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc, reply_message_id=reply_message_id)


def gmail_propose_send_draft(*, draft_id: str) -> dict[str, Any]:
    payload = {"draft_id": draft_id}
    return {
        "requires_confirmation": True,
        "action": "gmail_send_draft",
        "payload": payload,
        "confirmation_token": make_confirmation_token(action="gmail_send_draft", payload=payload),
        "message": "Ask the user to confirm before sending this draft.",
    }


def gmail_send_draft(*, draft_id: str, confirmation_token: str | None = None) -> dict[str, Any]:
    payload = {"draft_id": draft_id}
    require_confirmation(action="gmail_send_draft", payload=payload, confirmation_token=confirmation_token)
    return send_draft(draft_id=draft_id)
