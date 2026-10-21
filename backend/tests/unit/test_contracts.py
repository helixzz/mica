# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportOperatorIssue=false, reportGeneralTypeIssues=false

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import (
    Contract,
    ContractDocument,
    ContractStatus,
    ContractVersion,
    Department,
    Document,
    POStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)
from app.services import contracts as svc


def _suffix() -> str:
    return uuid4().hex[:8].upper()


async def _user(db, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _supplier(db, code: str = "SUP-DELL") -> Supplier:
    return (await db.execute(select(Supplier).where(Supplier.code == code))).scalar_one()


async def _create_contract(
    db,
    *,
    actor: User,
    supplier: Supplier,
    contract_number: str,
    title: str,
    expiry_date: date | None,
    status: str = ContractStatus.ACTIVE.value,
    notes: str | None = None,
    department_id: UUID | None = None,
) -> Contract:
    pr = PurchaseRequisition(
        pr_number=f"PR-CT-{_suffix()}",
        title="Contracts unit test PR",
        business_reason="unit test",
        status="draft",
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=department_id or actor.department_id,
        currency="CNY",
        total_amount=Decimal("1000.00"),
    )
    db.add(pr)
    await db.flush()

    po = PurchaseOrder(
        po_number=f"PO-CT-{_suffix()}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=POStatus.CONFIRMED.value,
        currency="CNY",
        total_amount=Decimal("1000.00"),
        amount_paid=Decimal("0"),
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()

    contract = Contract(
        contract_number=contract_number,
        po_id=po.id,
        supplier_id=supplier.id,
        title=title,
        status=status,
        currency="CNY",
        total_amount=Decimal("1000.00"),
        effective_date=date.today(),
        expiry_date=expiry_date,
        notes=notes,
    )
    db.add(contract)
    await db.flush()
    return contract


async def _attach_document(
    db,
    *,
    actor: User,
    contract: Contract,
    filename: str,
    role: str,
    display_order: int,
    ocr_text: str | None,
    created_at: datetime,
) -> tuple[ContractDocument, Document]:
    document = Document(
        storage_key=f"contracts/{_suffix()}-{filename}",
        storage_backend="local",
        original_filename=filename,
        content_type="application/pdf",
        file_size=2048,
        content_hash=uuid4().hex,
        doc_category="contract",
        is_private=True,
        uploaded_by_id=actor.id,
        created_at=created_at,
    )
    db.add(document)
    await db.flush()

    link = ContractDocument(
        contract_id=contract.id,
        document_id=document.id,
        role=role,
        ocr_text=ocr_text,
        display_order=display_order,
        created_at=created_at,
    )
    db.add(link)
    await db.flush()
    return link, document


async def test_expiring_contracts_returns_active_contracts_within_window(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    today = date.today()
    first = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="First expiring contract",
        expiry_date=today + timedelta(days=5),
    )
    second = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Second expiring contract",
        expiry_date=today + timedelta(days=12),
    )
    await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Outside window",
        expiry_date=today + timedelta(days=45),
    )
    await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Inactive contract",
        expiry_date=today + timedelta(days=7),
        status="draft",
    )

    rows = await svc.expiring_contracts(seeded_db_session, within_days=30)

    assert [row.id for row in rows] == [first.id, second.id]


async def test_expiring_contracts_uses_default_system_parameter_window(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session, "SUP-APPLE")
    today = date.today()
    within_default = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Default-window contract",
        expiry_date=today + timedelta(days=25),
    )
    await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Beyond default-window contract",
        expiry_date=today + timedelta(days=35),
    )

    rows = await svc.expiring_contracts(seeded_db_session)

    assert [row.id for row in rows] == [within_default.id]


async def test_search_contracts_empty_query_returns_empty(seeded_db_session):
    assert await svc.search_contracts(seeded_db_session, "   ") == []


async def test_search_contracts_non_matching_query_returns_empty(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Firewall Maintenance Agreement",
        expiry_date=date.today() + timedelta(days=60),
        notes="covers network devices",
    )
    await _attach_document(
        seeded_db_session,
        actor=actor,
        contract=contract,
        filename="maintenance.pdf",
        role="scan",
        display_order=0,
        ocr_text="annual service schedule",
        created_at=datetime.now(UTC),
    )

    assert await svc.search_contracts(seeded_db_session, "nonexistent phrase") == []


async def test_search_contracts_matching_query_returns_title_number_and_ocr_matches(
    seeded_db_session,
):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number="CT-VPN-001",
        title="VPN Support Contract",
        expiry_date=date.today() + timedelta(days=90),
        notes="corporate vpn renewal",
    )
    await _attach_document(
        seeded_db_session,
        actor=actor,
        contract=contract,
        filename="vpn.pdf",
        role="scan",
        display_order=0,
        ocr_text="VPN tunnel maintenance and support services",
        created_at=datetime.now(UTC),
    )

    rows = await svc.search_contracts(seeded_db_session, "vpn")

    assert len(rows) == 1
    result = rows[0]
    assert result["id"] == str(contract.id)
    assert result["contract_number"] == "CT-VPN-001"
    assert result["title"] == "VPN Support Contract"
    assert result["status"] == ContractStatus.ACTIVE.value
    assert result["expiry_date"] == contract.expiry_date.isoformat()
    assert result["total_amount"] == "1000.00"
    assert any(str(m).startswith("title:") for m in result["matched_in"])
    assert any(str(m).startswith("contract_number:") for m in result["matched_in"])
    assert any(str(match).startswith("ocr:…") for match in result["matched_in"])


async def test_to_dict_converts_contract_document_and_document_to_plain_dict(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Dictionary conversion contract",
        expiry_date=date.today() + timedelta(days=45),
    )
    link, document = await _attach_document(
        seeded_db_session,
        actor=actor,
        contract=contract,
        filename="contract-scan.pdf",
        role="scan",
        display_order=2,
        ocr_text="ocr text goes here",
        created_at=datetime.now(UTC),
    )

    payload = svc.to_dict(link, document)

    assert payload == {
        "document_id": str(document.id),
        "role": "scan",
        "display_order": 2,
        "has_ocr": True,
        "ocr_chars": 18,
        "original_filename": "contract-scan.pdf",
        "content_type": "application/pdf",
        "file_size": 2048,
    }


async def test_list_contract_versions_returns_descending_history(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Versioned Contract",
        expiry_date=date.today() + timedelta(days=30),
    )
    seeded_db_session.add_all(
        [
            ContractVersion(
                contract_id=contract.id,
                version_number=1,
                change_type="created",
                snapshot_json={"title": "Versioned Contract", "current_version": 1},
                changed_by_id=actor.id,
            ),
            ContractVersion(
                contract_id=contract.id,
                version_number=2,
                change_type="updated",
                snapshot_json={"title": "Versioned Contract v2", "current_version": 2},
                changed_by_id=actor.id,
            ),
        ]
    )
    await seeded_db_session.flush()

    rows = await svc.list_contract_versions(seeded_db_session, contract.id)

    assert [row.version_number for row in rows] == [2, 1]


async def test_list_contract_documents_returns_documents_for_contract_in_order(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session, "SUP-LENOVO")
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Ordered documents contract",
        expiry_date=date.today() + timedelta(days=75),
    )
    earlier = datetime.now(UTC) - timedelta(minutes=10)
    later = datetime.now(UTC)
    first_link, first_document = await _attach_document(
        seeded_db_session,
        actor=actor,
        contract=contract,
        filename="a.pdf",
        role="attachment",
        display_order=0,
        ocr_text=None,
        created_at=earlier,
    )
    second_link, second_document = await _attach_document(
        seeded_db_session,
        actor=actor,
        contract=contract,
        filename="b.pdf",
        role="scan",
        display_order=1,
        ocr_text="second document",
        created_at=later,
    )

    rows = await svc.list_contract_documents(seeded_db_session, contract.id)

    assert rows == [
        (first_link, first_document),
        (second_link, second_document),
    ]


async def _bare_document(db, actor: User, filename: str = "doc.pdf") -> Document:
    document = Document(
        storage_key=f"contracts/{_suffix()}-{filename}",
        storage_backend="local",
        original_filename=filename,
        content_type="application/pdf",
        file_size=1024,
        content_hash=uuid4().hex,
        doc_category="contract",
        is_private=True,
        uploaded_by_id=actor.id,
    )
    db.add(document)
    await db.flush()
    return document


async def test_attach_document_to_contract_without_ocr(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Attach Test",
        expiry_date=date.today() + timedelta(days=30),
    )
    document = await _bare_document(seeded_db_session, actor)

    link = await svc.attach_document_to_contract(
        seeded_db_session, actor.id, contract.id, document.id, run_ocr=False
    )

    assert link.contract_id == contract.id
    assert link.document_id == document.id
    assert link.ocr_text is None


async def test_attach_document_is_idempotent(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Idem Test",
        expiry_date=None,
    )
    document = await _bare_document(seeded_db_session, actor)

    link1 = await svc.attach_document_to_contract(
        seeded_db_session, actor.id, contract.id, document.id, run_ocr=False
    )
    link2 = await svc.attach_document_to_contract(
        seeded_db_session, actor.id, contract.id, document.id, run_ocr=False
    )
    assert link1.document_id == link2.document_id


async def test_attach_document_contract_not_found(seeded_db_session):
    actor = await _user(seeded_db_session)
    document = await _bare_document(seeded_db_session, actor)

    with pytest.raises(HTTPException) as exc:
        await svc.attach_document_to_contract(
            seeded_db_session, actor.id, uuid4(), document.id, run_ocr=False
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "contract.not_found"


async def test_attach_document_document_not_found(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Doc Missing",
        expiry_date=None,
    )

    with pytest.raises(HTTPException) as exc:
        await svc.attach_document_to_contract(
            seeded_db_session, actor.id, contract.id, uuid4(), run_ocr=False
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "document.not_found"


async def test_remove_contract_document(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Remove Test",
        expiry_date=None,
    )
    document = await _bare_document(seeded_db_session, actor)
    await svc.attach_document_to_contract(
        seeded_db_session, actor.id, contract.id, document.id, run_ocr=False
    )

    await svc.remove_contract_document(seeded_db_session, contract.id, document.id)

    link = (
        await seeded_db_session.execute(
            select(ContractDocument).where(
                ContractDocument.contract_id == contract.id,
                ContractDocument.document_id == document.id,
            )
        )
    ).scalar_one_or_none()
    assert link is None


async def test_remove_contract_document_not_found(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Remove Missing",
        expiry_date=None,
    )

    with pytest.raises(HTTPException) as exc:
        await svc.remove_contract_document(seeded_db_session, contract.id, uuid4())
    assert exc.value.status_code == 404


async def test_get_contract_version_by_number(seeded_db_session):
    actor = await _user(seeded_db_session)
    supplier = await _supplier(seeded_db_session)
    contract = await _create_contract(
        seeded_db_session,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-{_suffix()}",
        title="Version Test",
        expiry_date=None,
    )

    version = await svc.create_contract_version(
        seeded_db_session, contract=contract, actor=actor, change_type="created"
    )
    await seeded_db_session.commit()

    found = await svc.get_contract_version(seeded_db_session, contract.id, version.version_number)
    assert found is not None
    assert found.id == version.id

    missing = await svc.get_contract_version(seeded_db_session, contract.id, 9999)
    assert missing is None


async def test_search_contracts_matches_supplier_name_and_po_number(seeded_db_session):
    """Buyers search by supplier and PO number; contracts.search_text has neither."""
    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    contract = await _create_contract(
        db,
        actor=actor,
        supplier=supplier,
        contract_number=f"CT-SUP-{_suffix()}",
        title="Storage array maintenance",
        expiry_date=date.today() + timedelta(days=90),
        notes="renewal clause 9",
    )

    by_supplier = await svc.search_contracts(db, "戴尔", actor=actor)
    assert [row["id"] for row in by_supplier] == [str(contract.id)]
    assert any(m.startswith("supplier:") for m in by_supplier[0]["matched_in"])
    # The tag shows the matched text, not just the field name.
    assert "戴尔" in " ".join(by_supplier[0]["matched_in"])

    po_number = (
        await db.execute(select(PurchaseOrder.po_number).where(PurchaseOrder.id == contract.po_id))
    ).scalar_one()
    by_po = await svc.search_contracts(db, po_number, actor=actor)
    assert [row["id"] for row in by_po] == [str(contract.id)]
    assert any(m.startswith("po_number:") for m in by_po[0]["matched_in"])
    assert po_number in " ".join(by_po[0]["matched_in"])

    by_notes = await svc.search_contracts(db, "renewal clause", actor=actor)
    assert contract.id in {UUID(row["id"]) for row in by_notes}


async def test_search_contracts_respects_row_visibility(seeded_db_session):
    """Search must not be a way around the visibility the list endpoint applies."""
    db = seeded_db_session
    owner = await _user(db, "alice")
    manager = await _user(db, "bob")
    supplier = await _supplier(db)

    # alice and bob share a department in the seed, so park the PR in a brand new
    # department: bob is a dept_manager and may only see his own department.
    other_department = Department(
        company_id=owner.company_id,
        code=f"DEP-SCOPE-{_suffix()}",
        name_zh="范围测试部门",
        name_en="Scope Test Dept",
    )
    db.add(other_department)
    await db.flush()

    contract = await _create_contract(
        db,
        actor=owner,
        supplier=supplier,
        contract_number=f"CT-SCOPE-{_suffix()}",
        title="Scoped search target",
        expiry_date=date.today() + timedelta(days=30),
        department_id=other_department.id,
    )

    # alice is full-access, bob is scoped: same query, different visibility.
    visible_to_owner = await svc.search_contracts(db, "Scoped search target", actor=owner)
    assert contract.id in {UUID(row["id"]) for row in visible_to_owner}

    hidden_from_manager = await svc.search_contracts(db, "Scoped search target", actor=manager)
    assert contract.id not in {UUID(row["id"]) for row in hidden_from_manager}

    # Without an actor there is no scoping (kept for internal callers).
    unscoped = await svc.search_contracts(db, "Scoped search target")
    assert contract.id in {UUID(row["id"]) for row in unscoped}


async def _po_for_currency_test(db, actor, supplier, currency: str = "CNY") -> PurchaseOrder:
    from uuid import uuid4

    pr = PurchaseRequisition(
        pr_number=f"PR-CUR-{uuid4().hex[:6]}",
        title="币种测试",
        requester_id=actor.id,
        company_id=actor.company_id,
        status="approved",
        currency=currency,
        total_amount=Decimal("1000.00"),
    )
    db.add(pr)
    await db.flush()
    po = PurchaseOrder(
        po_number=f"PO-CUR-{uuid4().hex[:6]}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status=POStatus.CONFIRMED.value,
        currency=currency,
        total_amount=Decimal("1000.00"),
        amount_paid=Decimal("0"),
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()
    return po


async def test_a_mismatched_contract_currency_is_refused(seeded_db_session):
    """A contract's money follows its order — but the caller must be told.

    ContractCreateIn had no currency field, so Pydantic dropped the value and the
    contract quietly stored the order's. An API client setting HKD got CNY with a 201.
    """
    from app.services import flow as flow_svc

    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    po = await _po_for_currency_test(db, actor, supplier)

    with pytest.raises(HTTPException) as exc:
        await flow_svc.create_contract(
            db,
            actor,
            po.id,
            "币种不符的合同",
            Decimal("1000"),
            currency="HKD" if po.currency != "HKD" else "USD",
        )

    assert exc.value.status_code == 422
    assert "currency_follows_order" in str(exc.value.detail)


async def test_a_matching_contract_currency_is_accepted(seeded_db_session):
    from app.services import flow as flow_svc

    db = seeded_db_session
    actor = await _user(db)
    supplier = await _supplier(db)
    po = await _po_for_currency_test(db, actor, supplier)

    contract = await flow_svc.create_contract(
        db,
        actor,
        po.id,
        "币种一致的合同",
        Decimal("1000"),
        currency=po.currency,
    )

    assert contract.currency == po.currency
