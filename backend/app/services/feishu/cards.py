"""Feishu interactive-card builders (card JSON 2.0).

Cards are declared as data. The event templates in
:mod:`app.services.feishu.messages` only supply a headline and fields, so status
colour, spacing and the footer stay identical everywhere — and every label goes
through i18n instead of being glued together inside a business service.

Colour is semantic, not decorative: ``action`` (orange) is the only status that
means "a person is waiting for you". The old cards painted every event blue,
which is exactly why a pending approval looked like a receipt notice.
"""

from __future__ import annotations

from typing import Any

#: Feishu header templates keyed by the meaning of the card, not by hue.
STATUS_TEMPLATES: dict[str, str] = {
    "action": "orange",
    "success": "green",
    "warning": "red",
    "info": "blue",
    "neutral": "grey",
}


def _text(content: str) -> dict[str, str]:
    return {"tag": "plain_text", "content": content}


def card(
    *,
    title: str,
    status: str = "info",
    subtitle: str | None = None,
    elements: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    footer: str | None = None,
) -> dict[str, Any]:
    """Assemble a complete card 2.0 payload."""
    body: list[dict[str, Any]] = list(elements or [])
    if actions:
        body.append(action_row(actions))
    if footer:
        body.append(note(footer))

    header: dict[str, Any] = {
        "title": _text(title),
        "template": STATUS_TEMPLATES.get(status, STATUS_TEMPLATES["info"]),
    }
    if subtitle:
        header["subtitle"] = _text(subtitle)

    return {
        "schema": "2.0",
        "config": {"wide_screen_mode": True, "update_multi": True},
        "header": header,
        "body": {"elements": body},
    }


def markdown(content: str) -> dict[str, Any]:
    return {"tag": "markdown", "content": content}


def divider() -> dict[str, Any]:
    return {"tag": "hr"}


def note(content: str) -> dict[str, Any]:
    return {"tag": "note", "elements": [_text(content)]}


def label_value(label: str, value: str) -> dict[str, Any]:
    """One two-line cell: dim label above a bold value."""
    return markdown(f"<font color='grey'>{label}</font>\n**{value}**")


def field_rows(fields: list[tuple[str, str]], *, per_row: int = 2) -> list[dict[str, Any]]:
    """Lay key/value pairs out as a grid instead of one markdown line per field."""
    if not fields:
        return []

    cells = [label_value(label, value) for label, value in fields]
    while len(cells) % per_row:
        cells.append(markdown(" "))

    rows: list[dict[str, Any]] = []
    for index in range(0, len(cells), per_row):
        rows.append(
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "elements": [cell],
                    }
                    for cell in cells[index : index + per_row]
                ],
            }
        )
    return rows


def table(
    columns: list[tuple[str, str]],
    rows: list[dict[str, str]],
    *,
    page_size: int = 5,
) -> dict[str, Any]:
    """Compact table for multi-row detail (line items, digest top-N)."""
    return {
        "tag": "table",
        "page_size": max(1, min(page_size, 10)),
        "row_height": "low",
        "header_style": {"background_style": "grey", "bold": True, "lines": 1},
        "columns": [
            {"name": name, "display_name": display, "data_type": "text", "width": "auto"}
            for name, display in columns
        ],
        "rows": rows,
    }


def button(text: str, url: str, *, primary: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tag": "button",
        "text": _text(text),
        "type": "primary" if primary else "default",
    }
    if url:
        # 2.0 buttons declare navigation as a behaviour; the legacy `url` field is
        # kept as well so an older client renders the same destination.
        payload["behaviors"] = [{"type": "open_url", "default_url": url}]
        payload["url"] = url
    return payload


def action_row(actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"tag": "action", "actions": actions}


def bullet_list(items: list[str], *, empty: str | None = None) -> dict[str, Any]:
    if not items:
        return markdown(empty or "—")
    return markdown("\n".join(f"• {item}" for item in items))
