from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password
from app.models import (
    AIFeatureRouting,
    AIModel,
    Company,
    Department,
    Item,
    Supplier,
    User,
    UserRole,
)

settings = get_settings()


async def seed_dev_data(db: AsyncSession) -> None:
    existing = await db.execute(select(Company).where(Company.code == "DEMO"))
    if existing.scalar_one_or_none():
        await _seed_ai_if_missing(db)
        return

    company = Company(
        code="DEMO",
        name_zh="觅采演示公司",
        name_en="Mica Demo Co., Ltd.",
        default_locale="zh-CN",
        default_currency="CNY",
    )
    db.add(company)
    await db.flush()

    dept_it = Department(company_id=company.id, code="IT", name_zh="IT 部", name_en="IT Department")
    dept_fin = Department(
        company_id=company.id, code="FIN", name_zh="财务部", name_en="Finance Department"
    )
    dept_proc = Department(
        company_id=company.id, code="PROC", name_zh="采购部", name_en="Procurement Department"
    )
    db.add_all([dept_it, dept_fin, dept_proc])
    await db.flush()

    pwd = hash_password(settings.seed_default_password)
    users = [
        User(
            username="admin",
            email="admin@mica.local",
            display_name="管理员 Admin",
            password_hash=pwd,
            role=UserRole.ADMIN.value,
            company_id=company.id,
            department_id=None,
            preferred_locale="zh-CN",
            is_local_admin=True,
        ),
        User(
            username="alice",
            email="alice@mica.local",
            display_name="Alice （IT 采购员）",
            password_hash=pwd,
            role=UserRole.IT_BUYER.value,
            company_id=company.id,
            department_id=dept_it.id,
            preferred_locale="zh-CN",
        ),
        User(
            username="bob",
            email="bob@mica.local",
            display_name="Bob （IT 部负责人）",
            password_hash=pwd,
            role=UserRole.DEPT_MANAGER.value,
            company_id=company.id,
            department_id=dept_it.id,
            preferred_locale="zh-CN",
        ),
        User(
            username="carol",
            email="carol@mica.local",
            display_name="Carol (Finance Auditor)",
            password_hash=pwd,
            role=UserRole.FINANCE_AUDITOR.value,
            company_id=company.id,
            department_id=dept_fin.id,
            preferred_locale="en-US",
        ),
        User(
            username="dave",
            email="dave@mica.local",
            display_name="Dave (Procurement Manager)",
            password_hash=pwd,
            role=UserRole.PROCUREMENT_MGR.value,
            company_id=company.id,
            department_id=dept_proc.id,
            preferred_locale="en-US",
        ),
    ]
    db.add_all(users)

    suppliers = [
        Supplier(
            code="SUP-DELL",
            name="戴尔（中国）有限公司 / Dell China Ltd.",
            contact_name="张经理",
            contact_phone="021-12345678",
            contact_email="sales@dell-demo.local",
            tax_number="91310000MA1K000001",
        ),
        Supplier(
            code="SUP-LENOVO",
            name="联想（中国）有限公司 / Lenovo China",
            contact_name="李经理",
            contact_phone="010-87654321",
            contact_email="sales@lenovo-demo.local",
            tax_number="91100000MA1K000002",
        ),
        Supplier(
            code="SUP-APPLE",
            name="苹果贸易（上海）有限公司 / Apple Trading",
            contact_name="王经理",
            contact_phone="021-55556666",
            contact_email="corp@apple-demo.local",
            tax_number="91310000MA1K000003",
        ),
    ]
    db.add_all(suppliers)

    items = [
        Item(
            code="SKU-SRV-R750",
            name="Dell PowerEdge R750 服务器",
            category="server",
            uom="EA",
            specification="2× Intel Xeon Gold 6338, 256GB RAM, 4× 1.92TB SSD",
            requires_serial=True,
        ),
        Item(
            code="SKU-NB-T14",
            name="ThinkPad T14 Gen5",
            category="laptop",
            uom="EA",
            specification='Intel Core Ultra 7, 32GB RAM, 1TB SSD, 14" 2.2K',
            requires_serial=True,
        ),
        Item(
            code="SKU-NB-MBP16",
            name="MacBook Pro 16 M4 Pro",
            category="laptop",
            uom="EA",
            specification="M4 Pro, 48GB RAM, 1TB SSD",
            requires_serial=True,
        ),
        Item(
            code="SKU-MON-U2723",
            name="Dell UltraSharp U2723QE",
            category="monitor",
            uom="EA",
            specification='27" 4K IPS USB-C Hub Monitor',
            requires_serial=True,
        ),
        Item(
            code="SKU-SW-M365",
            name="Microsoft 365 商业标准版订阅",
            category="software",
            uom="YEAR",
            specification="12 个月订阅，每用户",
        ),
        Item(
            code="SKU-SRV-R760",
            name="Dell PowerEdge R760 服务器",
            category="server",
            uom="EA",
            specification="2× Intel Xeon Gold 6430, 512GB RAM, 8× 3.84TB NVMe",
            requires_serial=True,
        ),
        Item(
            code="SKU-NET-S5248",
            name="Dell Networking S5248F-ON 交换机",
            category="network",
            uom="EA",
            specification="48x 25GbE SFP28 + 8x 100GbE QSFP28",
            requires_serial=True,
        ),
    ]
    db.add_all(items)

    await db.commit()
    await _seed_ai_if_missing(db)


async def _seed_ai_if_missing(db: AsyncSession) -> None:
    existing = (
        await db.execute(select(AIModel).where(AIModel.name == "demo-mock"))
    ).scalar_one_or_none()
    if existing is not None:
        return

    demo_model = AIModel(
        name="demo-mock",
        provider="mock",
        model_string="mock/demo",
        modality="text",
        api_base=None,
        api_key_encrypted=None,
        is_active=True,
        priority=100,
        capabilities={"streaming": True, "json_mode": False, "vision": False},
    )
    db.add(demo_model)
    await db.flush()

    vision_placeholder = AIModel(
        name="demo-vision-placeholder",
        provider="mock",
        model_string="mock/vision",
        modality="vision",
        api_base=None,
        api_key_encrypted=None,
        is_active=False,
        priority=100,
        capabilities={"streaming": True, "json_mode": True, "vision": True},
    )
    db.add(vision_placeholder)
    await db.flush()

    db.add_all(
        [
            AIFeatureRouting(
                feature_code="pr_description_polish",
                primary_model_id=demo_model.id,
                temperature=Decimal("0.30"),
                max_tokens=512,
                enabled=True,
            ),
            AIFeatureRouting(
                feature_code="sku_suggest",
                primary_model_id=demo_model.id,
                temperature=Decimal("0.20"),
                max_tokens=400,
                enabled=True,
            ),
            AIFeatureRouting(
                feature_code="invoice_extract",
                primary_model_id=vision_placeholder.id,
                temperature=Decimal("0.10"),
                max_tokens=1500,
                enabled=True,
            ),
            AIFeatureRouting(
                feature_code="document_generation",
                primary_model_id=demo_model.id,
                temperature=Decimal("0.00"),
                max_tokens=1200,
                enabled=False,
            ),
        ]
    )
    await db.commit()
