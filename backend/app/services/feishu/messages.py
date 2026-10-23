"""Feishu card templates for Mica's business events.

Each builder receives already-formatted values (money via :func:`fmt_amount`,
dates via :func:`fmt_date`) and a locale, and returns a card 2.0 payload. No
builder decides what happened — that is the notification's job — so a template
can be reused by the in-app notification copy without drifting.
"""

from __future__ import annotations

from typing import Any

from app.i18n import t
from app.services.feishu import cards


def _label(locale: str, key: str) -> str:
    return t(f"feishu.card.label.{key}", locale)


def _footer(locale: str) -> str:
    return t("feishu.card.footer", locale)


def _headline(locale: str, key: str, **kwargs: object) -> str:
    return t(f"feishu.card.headline.{key}", locale, **kwargs)


def _button(locale: str, key: str, url: str, *, primary: bool = False) -> dict[str, Any] | None:
    if not url:
        return None
    return cards.button(t(f"feishu.card.action.{key}", locale), url, primary=primary)


def build_pr_submitted_card(
    *,
    pr_number: str,
    title: str,
    applicant: str,
    department: str,
    amount: str,
    line_count: int,
    item_count: int,
    waiting_hours: float | None,
    sla_hours: int | None,
    task_url: str,
    pr_url: str,
    locale: str,
) -> dict[str, Any]:
    subtitle_parts: list[str] = []
    if waiting_hours is not None:
        subtitle_parts.append(t("feishu.card.waiting", locale, hours=f"{waiting_hours:.1f}"))
    if sla_hours is not None:
        subtitle_parts.append(t("feishu.card.sla", locale, hours=sla_hours))

    fields = [
        (_label(locale, "amount"), amount),
        (
            _label(locale, "lines"),
            t("feishu.card.lines_value", locale, lines=line_count, items=item_count),
        ),
        (_label(locale, "applicant"), applicant),
        (_label(locale, "department"), department or "—"),
    ]

    elements: list[dict[str, Any]] = [
        cards.markdown(f"**{pr_number}**　{title}"),
        *cards.field_rows(fields),
    ]

    actions = [
        button
        for button in (
            _button(locale, "review", task_url, primary=True),
            _button(locale, "view_pr", pr_url),
        )
        if button is not None
    ]

    return cards.card(
        title=_headline(locale, "pr_submitted", applicant=applicant),
        subtitle=" · ".join(subtitle_parts) or None,
        status="action",
        elements=elements,
        actions=actions,
        footer=_footer(locale),
    )


def build_approval_decided_card(
    *,
    pr_number: str,
    title: str,
    decider: str,
    result: str,
    comment: str,
    amount: str,
    pr_url: str,
    locale: str,
) -> dict[str, Any]:
    status = "success" if result == "approved" else "warning"
    headline_key = {
        "approved": "approved",
        "rejected": "rejected",
        "returned": "returned",
    }.get(result, "approved")

    fields = [
        (_label(locale, "amount"), amount),
        (_label(locale, "result"), t(f"feishu.card.result.{result}", locale)),
        (_label(locale, "decider"), decider or "—"),
    ]

    elements: list[dict[str, Any]] = [
        cards.markdown(f"**{pr_number}**　{title}"),
        *cards.field_rows(fields),
    ]
    if comment:
        elements.append(cards.divider())
        elements.append(cards.markdown(f"**{_label(locale, 'comment')}**\n{comment}"))

    action = _button(locale, "view_pr", pr_url, primary=(result != "approved"))

    return cards.card(
        title=_headline(locale, headline_key),
        status=status,
        elements=elements,
        actions=[action] if action else None,
        footer=_footer(locale),
    )


def build_po_created_card(
    *,
    po_number: str,
    supplier: str,
    amount: str,
    pr_title: str,
    po_url: str,
    locale: str,
) -> dict[str, Any]:
    fields = [
        (_label(locale, "amount"), amount),
        (_label(locale, "supplier"), supplier or "—"),
        (_label(locale, "po"), po_number),
    ]
    if pr_title:
        fields.append((_label(locale, "pr_title"), pr_title))

    action = _button(locale, "view_po", po_url)

    return cards.card(
        title=_headline(locale, "po_created", supplier=supplier or po_number),
        status="info",
        elements=[cards.markdown(f"**{po_number}**"), *cards.field_rows(fields)],
        actions=[action] if action else None,
        footer=_footer(locale),
    )


def build_payment_pending_card(
    *,
    payment_number: str,
    po_number: str,
    supplier: str,
    amount: str,
    due_date: str,
    payment_url: str,
    locale: str,
) -> dict[str, Any]:
    fields = [
        (_label(locale, "amount"), amount),
        (_label(locale, "supplier"), supplier or "—"),
        (_label(locale, "po"), po_number or "—"),
        (_label(locale, "due"), due_date or "—"),
    ]
    action = _button(locale, "view_payment", payment_url)

    return cards.card(
        title=_headline(locale, "payment_pending"),
        subtitle=payment_number,
        status="action",
        elements=cards.field_rows(fields),
        actions=[action] if action else None,
        footer=_footer(locale),
    )


def build_contract_expiring_card(
    *,
    contract_number: str,
    supplier: str,
    expiry_date: str,
    days_remaining: int,
    total_amount: str,
    used_amount: str,
    contract_url: str,
    locale: str,
) -> dict[str, Any]:
    status = "warning" if days_remaining <= 7 else "action"
    fields = [
        (_label(locale, "supplier"), supplier or "—"),
        (_label(locale, "expiry"), expiry_date),
        (_label(locale, "days_left"), t("feishu.card.days", locale, days=days_remaining)),
        (_label(locale, "amount"), total_amount),
        (_label(locale, "used"), used_amount),
    ]
    action = _button(locale, "view_contract", contract_url)

    return cards.card(
        title=_headline(locale, "contract_expiring", number=contract_number),
        subtitle=t("feishu.card.days", locale, days=days_remaining),
        status=status,
        elements=cards.field_rows(fields),
        actions=[action] if action else None,
        footer=_footer(locale),
    )


def build_event_card(
    *,
    title: str,
    summary: str = "",
    fields: list[tuple[str, str]] | None = None,
    changes: list[tuple[str, str]] | None = None,
    url: str = "",
    status: str = "info",
    locale: str,
) -> dict[str, Any]:
    """Generic announcement card: PR/contract/shipment updates and the like."""
    elements: list[dict[str, Any]] = []
    if summary:
        elements.append(cards.markdown(summary))
    if fields:
        elements.extend(cards.field_rows(fields))
    if changes:
        elements.append(cards.divider())
        rows = "\n".join(f"• **{label}**: {value}" for label, value in changes)
        elements.append(cards.markdown(rows))

    action = _button(locale, "view", url)

    return cards.card(
        title=title,
        status=status,
        elements=elements,
        actions=[action] if action else None,
        footer=_footer(locale),
    )
