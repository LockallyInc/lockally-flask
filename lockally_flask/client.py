"""Shared Lockally send client used by the Flask extension.

Wraps the core `lockally` SDK's SendApi with a friendly `send_email(...)` that maps
keyword arguments onto the `POST /v1/send` body (Reply-To -> headers, attachments ->
base64, one Idempotency-Key per send). Sandbox vs. live is implicit in the API key
prefix (`lk_test_` / `lk_live_`), so no separate endpoint is needed.
"""

from __future__ import annotations

import base64
import uuid
from email.utils import parseaddr
from typing import Any, Iterable, Sequence


class LockallyClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 send_api: Any = None) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._send_api = send_api  # injectable for tests

    # -- delivery ---------------------------------------------------------------

    def send_email(self, *, from_: str, to: str | Sequence[str],
                   subject: str | None = None, text: str | None = None,
                   html: str | None = None, cc: str | Sequence[str] | None = None,
                   bcc: str | Sequence[str] | None = None,
                   reply_to: str | Sequence[str] | None = None,
                   headers: dict[str, str] | None = None,
                   attachments: Iterable[tuple] | None = None) -> Any:
        """Send one message. Returns the SDK's `V1SendPost202Response`.

        `to`/`cc`/`bcc`/`reply_to` accept a single address or a list. `attachments`
        is an iterable of `(filename, content, content_type)` where content is bytes
        or str.
        """
        request = self._to_request(self.build_payload(
            from_=from_, to=to, subject=subject, text=text, html=html,
            cc=cc, bcc=bcc, reply_to=reply_to, headers=headers, attachments=attachments,
        ))
        return self._get_send_api().v1_send_post(self._idempotency_key(), request)

    # -- mapping ----------------------------------------------------------------

    @staticmethod
    def build_payload(*, from_: str, to: str | Sequence[str],
                      subject: str | None = None, text: str | None = None,
                      html: str | None = None, cc: str | Sequence[str] | None = None,
                      bcc: str | Sequence[str] | None = None,
                      reply_to: str | Sequence[str] | None = None,
                      headers: dict[str, str] | None = None,
                      attachments: Iterable[tuple] | None = None) -> dict:
        """Map keyword arguments onto the /v1/send JSON body. Returns a plain dict
        so the mapping is unit-testable without the SDK models."""
        payload: dict[str, Any] = {
            "from": _addr(from_),
            "to": [_addr(a) for a in _as_list(to)],
        }
        if cc:
            payload["cc"] = [_addr(a) for a in _as_list(cc)]
        if bcc:
            payload["bcc"] = [_addr(a) for a in _as_list(bcc)]
        if subject:
            payload["subject"] = subject
        if text:
            payload["text"] = text
        if html:
            payload["html"] = html

        out_headers = dict(headers or {})
        if reply_to:
            # Lockally has no reply_to field — carry it as a header.
            out_headers["Reply-To"] = ", ".join(_as_list(reply_to))
        if out_headers:
            payload["headers"] = out_headers

        parts = []
        for attachment in (attachments or []):
            filename, content, content_type = (list(attachment) + [None, None, None])[:3]
            if content is None:
                continue
            raw = content.encode() if isinstance(content, str) else content
            parts.append({
                "filename": filename or "attachment",
                "content_type": content_type or "application/octet-stream",
                "content_base64": base64.b64encode(raw).decode("ascii"),
            })
        if parts:
            payload["attachments"] = parts

        return payload

    def _to_request(self, payload: dict):
        from lockally.models.v1_send_post_request import V1SendPostRequest
        return V1SendPostRequest.from_dict(payload)

    # -- client -----------------------------------------------------------------

    def _get_send_api(self):
        if self._send_api is None:
            from lockally import ApiClient, Configuration
            from lockally.api.send_api import SendApi
            cfg = Configuration(access_token=self._api_key)
            if self._base_url:
                cfg.host = self._base_url.rstrip("/")
            self._send_api = SendApi(ApiClient(cfg))
        return self._send_api

    @staticmethod
    def _idempotency_key() -> str:
        return "lk-" + uuid.uuid4().hex


def _as_list(value: str | Sequence[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    return list(value)


def _addr(value: str) -> str:
    """Extract the bare email address from a possibly `Name <addr>` string."""
    return parseaddr(value)[1] or value
