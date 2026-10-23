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


def build_invoice_card(
    *,
    invoice_number: str,
    vendor_number: str,
    supplier: str,
    total_amount: str,
    invoice_date: str,
    tax_note: str,
    matched: bool,
    po_hint: str,
    created_by: str,
    invoice_url: str,
    locale: str,
) -> dict[str, Any]:
    """One card for "an invoice arrived" — creation and 3-way match in one.

    Sending a creation card and a match card separately said the same thing
    twice, and listed subtotal/tax even when they only repeated the total.
    """
    meta = " · ".join(
        part
        for part in (
            invoice_date,
            tax_note,
            f"{_label(locale, 'vendor_number')} {vendor_number}" if vendor_number else "",
            created_by,
        )
        if part
    )
    match_text = (
        t("feishu.card.invoice.matched", locale, po=po_hint or "—")
        if matched
        else t("feishu.card.invoice.unmatched", locale)
    )
    action = _button(locale, "view_invoice", invoice_url)

    return cards.card(
        title=(
            t("feishu.card.headline.invoice_created", locale, number=invoice_number)
            if matched
            else t("feishu.card.headline.invoice_needs_review", locale, number=invoice_number)
        ),
        subtitle=supplier,
        status="success" if matched else "warning",
        elements=[
            cards.hero(total_amount, supplier),
            cards.meta_line([meta]) if meta else cards.markdown(" "),
            cards.divider(),
            cards.status_line(matched, match_text),
        ],
        actions=[action] if action else None,
        footer=_footer(locale),
    )


def build_po_receipt_card(
    *,
    po_number: str,
    pr_title: str,
    received: str,
    ordered: str,
    percent: str,
    shipment_number: str,
    carrier: str,
    tracking: str,
    fully_received: bool,
    po_url: str,
    locale: str,
) -> dict[str, Any]:
    """Receipt cards lead with the quantity progress, not with the PO number."""
    action = _button(locale, "view_po", po_url)
    progress = f"{received} / {ordered}"
    meta = " · ".join(part for part in (pr_title, carrier, tracking, shipment_number) if part)

    elements: list[dict[str, Any]] = [
        cards.hero(progress, t("feishu.card.received_caption", locale, percent=percent)),
        cards.meta_line([meta]) if meta else cards.markdown(" "),
        cards.divider(),
        cards.status_line(
            fully_received,
            t("feishu.card.receipt.complete", locale)
            if fully_received
            else t("feishu.card.receipt.partial", locale),
        ),
    ]

    return cards.card(
        title=t(
            "feishu.card.headline.po_receipt",
            locale,
            number=po_number,
            state=t("feishu.card.receipt.state", locale)
            if fully_received
            else t("feishu.card.receipt.state_partial", locale),
        ),
        status="success" if fully_received else "action",
        elements=elements,
        actions=[action] if action else None,
        footer=_footer(locale),
    )
