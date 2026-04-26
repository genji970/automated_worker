from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from serving.tools.google.gmail_tools import (
    gmail_apply_label as _gmail_apply_label,
    gmail_archive_messages as _gmail_archive_messages,
    gmail_create_draft as _gmail_create_draft,
    gmail_list_labels as _gmail_list_labels,
    gmail_mark_read as _gmail_mark_read,
    gmail_mark_unread as _gmail_mark_unread,
    gmail_propose_apply_label as _gmail_propose_apply_label,
    gmail_propose_archive_messages as _gmail_propose_archive_messages,
    gmail_propose_mark_read as _gmail_propose_mark_read,
    gmail_propose_mark_unread as _gmail_propose_mark_unread,
    gmail_propose_send_draft as _gmail_propose_send_draft,
    gmail_propose_trash_messages as _gmail_propose_trash_messages,
    gmail_read_messages as _gmail_read_messages,
    gmail_search_messages as _gmail_search_messages,
    gmail_send_draft as _gmail_send_draft,
    gmail_trash_messages as _gmail_trash_messages,
)


mcp = FastMCP("serving-gmail-tools")


@mcp.tool()
def gmail_list_labels() -> dict[str, Any]:
    """List Gmail labels. Use this when the user asks about available Gmail labels or label ids."""
    return _gmail_list_labels()


@mcp.tool()
def gmail_search_messages(
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
    """Search Gmail messages. Use for finding, reviewing, filtering, or summarizing emails. For Korean requests like '어제 내 메일 중 스팸 아닌 거 골라줘', use date_preset='yesterday', exclude_spam=True, exclude_trash=True."""
    return _gmail_search_messages(
        query=query,
        date_preset=date_preset,
        after=after,
        before=before,
        exclude_spam=exclude_spam,
        exclude_trash=exclude_trash,
        extra_query=extra_query,
        unread_only=unread_only,
        max_results=max_results,
    )


@mcp.tool()
def gmail_read_messages(message_ids: list[str], include_body: bool = True, limit: int = 10) -> dict[str, Any]:
    """Read selected Gmail messages by message id. Use after gmail_search_messages when body content is needed for classification or summarization."""
    return _gmail_read_messages(message_ids=message_ids, include_body=include_body, limit=limit)


@mcp.tool()
def gmail_propose_archive_messages(message_ids: list[str]) -> dict[str, Any]:
    """Prepare an archive action and return a confirmation token. Call this before archiving emails, then ask the user to confirm."""
    return _gmail_propose_archive_messages(message_ids=message_ids)


@mcp.tool()
def gmail_archive_messages(message_ids: list[str], confirmation_token: str) -> dict[str, Any]:
    """Archive Gmail messages by removing the INBOX label. Requires a confirmation token from gmail_propose_archive_messages after explicit user confirmation."""
    return _gmail_archive_messages(message_ids=message_ids, confirmation_token=confirmation_token)


@mcp.tool()
def gmail_propose_apply_label(
    message_ids: list[str],
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Prepare a Gmail label modification and return a confirmation token. Call this before changing labels, then ask the user to confirm."""
    return _gmail_propose_apply_label(
        message_ids=message_ids,
        add_label_ids=add_label_ids,
        remove_label_ids=remove_label_ids,
    )


@mcp.tool()
def gmail_apply_label(
    message_ids: list[str],
    confirmation_token: str,
    add_label_ids: list[str] | None = None,
    remove_label_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Apply or remove Gmail labels by label id. Requires a confirmation token from gmail_propose_apply_label after explicit user confirmation."""
    return _gmail_apply_label(
        message_ids=message_ids,
        add_label_ids=add_label_ids,
        remove_label_ids=remove_label_ids,
        confirmation_token=confirmation_token,
    )


@mcp.tool()
def gmail_propose_trash_messages(message_ids: list[str]) -> dict[str, Any]:
    """Prepare moving Gmail messages to trash and return a confirmation token. Call this before trashing emails, then ask the user to confirm."""
    return _gmail_propose_trash_messages(message_ids=message_ids)


@mcp.tool()
def gmail_trash_messages(message_ids: list[str], confirmation_token: str) -> dict[str, Any]:
    """Move Gmail messages to trash. Requires a confirmation token from gmail_propose_trash_messages after explicit user confirmation."""
    return _gmail_trash_messages(message_ids=message_ids, confirmation_token=confirmation_token)


@mcp.tool()
def gmail_propose_mark_read(message_ids: list[str]) -> dict[str, Any]:
    """Prepare marking Gmail messages as read and return a confirmation token. Call this before changing read state."""
    return _gmail_propose_mark_read(message_ids=message_ids)


@mcp.tool()
def gmail_mark_read(message_ids: list[str], confirmation_token: str) -> dict[str, Any]:
    """Mark Gmail messages as read. Requires confirmation token from gmail_propose_mark_read."""
    return _gmail_mark_read(message_ids=message_ids, confirmation_token=confirmation_token)


@mcp.tool()
def gmail_propose_mark_unread(message_ids: list[str]) -> dict[str, Any]:
    """Prepare marking Gmail messages as unread and return a confirmation token. Call this before changing read state."""
    return _gmail_propose_mark_unread(message_ids=message_ids)


@mcp.tool()
def gmail_mark_unread(message_ids: list[str], confirmation_token: str) -> dict[str, Any]:
    """Mark Gmail messages as unread. Requires confirmation token from gmail_propose_mark_unread."""
    return _gmail_mark_unread(message_ids=message_ids, confirmation_token=confirmation_token)


@mcp.tool()
def gmail_create_draft(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    reply_message_id: str | None = None,
) -> dict[str, Any]:
    """Create a Gmail draft. This does not send the email. Use when the user asks to draft a reply or email."""
    return _gmail_create_draft(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        reply_message_id=reply_message_id,
    )


@mcp.tool()
def gmail_propose_send_draft(draft_id: str) -> dict[str, Any]:
    """Prepare sending a Gmail draft and return a confirmation token. Call this before sending, then ask the user to confirm."""
    return _gmail_propose_send_draft(draft_id=draft_id)


@mcp.tool()
def gmail_send_draft(draft_id: str, confirmation_token: str) -> dict[str, Any]:
    """Send an existing Gmail draft. Requires a confirmation token from gmail_propose_send_draft after explicit user confirmation."""
    return _gmail_send_draft(draft_id=draft_id, confirmation_token=confirmation_token)


if __name__ == "__main__":
    mcp.run()
