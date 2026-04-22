"""enrich procurement categories and items

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        INSERT INTO procurement_categories (id, code, label_zh, label_en, sort_order, level, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'desktop',     '台式机',     'Desktops',          7,  1, now(), now()),
            (gen_random_uuid(), 'monitor',     '显示器',     'Monitors',          8,  1, now(), now()),
            (gen_random_uuid(), 'peripheral',  '外设配件',   'Peripherals',       9,  1, now(), now()),
            (gen_random_uuid(), 'storage',     '存储设备',   'Storage Devices',   10, 1, now(), now()),
            (gen_random_uuid(), 'cloud',       '云服务',     'Cloud Services',    11, 1, now(), now()),
            (gen_random_uuid(), 'office',      '办公用品',   'Office Supplies',   12, 1, now(), now()),
            (gen_random_uuid(), 'furniture',   '办公家具',   'Office Furniture',  13, 1, now(), now())
        ON CONFLICT (code) DO NOTHING
    """)
    )

    op.execute(
        sa.text("""
        INSERT INTO procurement_categories (id, code, label_zh, label_en, sort_order, level, parent_id, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'gpu',       'GPU',         'GPU',         5, 2, (SELECT id FROM procurement_categories WHERE code='server_parts'), now(), now()),
            (gen_random_uuid(), 'psu',       '电源',        'PSU',         6, 2, (SELECT id FROM procurement_categories WHERE code='server_parts'), now(), now()),
            (gen_random_uuid(), 'switch',    '交换机',      'Switch',      1, 2, (SELECT id FROM procurement_categories WHERE code='network'),      now(), now()),
            (gen_random_uuid(), 'router',    '路由器',      'Router',      2, 2, (SELECT id FROM procurement_categories WHERE code='network'),      now(), now()),
            (gen_random_uuid(), 'firewall',  '防火墙',      'Firewall',    3, 2, (SELECT id FROM procurement_categories WHERE code='network'),      now(), now()),
            (gen_random_uuid(), 'ap',        '无线 AP',     'Wireless AP', 4, 2, (SELECT id FROM procurement_categories WHERE code='network'),      now(), now()),
            (gen_random_uuid(), 'os',        '操作系统',    'OS License',  1, 2, (SELECT id FROM procurement_categories WHERE code='software'),     now(), now()),
            (gen_random_uuid(), 'db_license','数据库许可',  'DB License',  2, 2, (SELECT id FROM procurement_categories WHERE code='software'),     now(), now()),
            (gen_random_uuid(), 'saas',      'SaaS 订阅',   'SaaS',        3, 2, (SELECT id FROM procurement_categories WHERE code='software'),     now(), now()),
            (gen_random_uuid(), 'nas',       'NAS',          'NAS',         1, 2, (SELECT id FROM procurement_categories WHERE code='storage'),      now(), now()),
            (gen_random_uuid(), 'san',       'SAN',          'SAN',         2, 2, (SELECT id FROM procurement_categories WHERE code='storage'),      now(), now()),
            (gen_random_uuid(), 'tape',      '磁带库',      'Tape Library', 3, 2, (SELECT id FROM procurement_categories WHERE code='storage'),     now(), now())
        ON CONFLICT (code) DO NOTHING
    """)
    )

    op.execute(
        sa.text("""
        INSERT INTO items (id, code, name, category, uom, specification, requires_serial, is_active, created_at, updated_at,
                          category_id)
        VALUES
            (gen_random_uuid(), 'SRV-MEM-96GB',   '96GB RDIMM DDR5 6400MT/s',         'memory',  'EA', '96GB 2Rx4 DDR5-6400 RDIMM ECC',                  false, true, now(), now(), (SELECT id FROM procurement_categories WHERE code='memory')),
            (gen_random_uuid(), 'SRV-MEM-64GB',   '64GB RDIMM DDR5 5600MT/s',         'memory',  'EA', '64GB 2Rx4 DDR5-5600 RDIMM ECC',                  false, true, now(), now(), (SELECT id FROM procurement_categories WHERE code='memory')),
            (gen_random_uuid(), 'SRV-SSD-3.84T',  '3.84TB NVMe U.2 SSD',              'ssd',     'EA', '3.84TB NVMe U.2 Mixed Use SSD PCIe 4.0',         true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='ssd')),
            (gen_random_uuid(), 'SRV-SSD-1.92T',  '1.92TB NVMe U.2 SSD',              'ssd',     'EA', '1.92TB NVMe U.2 Read Intensive SSD PCIe 4.0',    true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='ssd')),
            (gen_random_uuid(), 'SRV-CPU-GOLD',   'Intel Xeon Gold 6458Q',             'cpu',     'EA', '32C/64T 3.1GHz 350W TDP LGA4677',                true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='cpu')),
            (gen_random_uuid(), 'SRV-GPU-H100',   'NVIDIA H100 80GB PCIe',             'gpu',     'EA', 'H100 80GB HBM3 PCIe 5.0 x16 700W',               true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='gpu')),
            (gen_random_uuid(), 'SRV-NIC-100G',   '100GbE 双口网卡',                  'nic',     'EA', '100GbE QSFP56 双口 PCIe 4.0 x16',                true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='nic')),
            (gen_random_uuid(), 'NET-SW-48P',     '48 口万兆交换机',                  'switch',  'EA', '48x 10GbE SFP+ / 6x 100GbE QSFP28 / L3 堆叠',  true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='switch')),
            (gen_random_uuid(), 'NET-FW-NGFW',    '下一代防火墙',                      'firewall','EA', '40Gbps 吞吐 / IPS / SSL 解密 / SD-WAN',          true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='firewall')),
            (gen_random_uuid(), 'NET-AP-WIFI7',   'Wi-Fi 7 无线接入点',                'ap',      'EA', 'Wi-Fi 7 (802.11be) 三频 / PoE++ / 室内吸顶',     true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='ap')),
            (gen_random_uuid(), 'LAPTOP-THINKPAD','ThinkPad X1 Carbon Gen12',          'laptop',  'EA', '14" 2.8K OLED / Ultra 7 165H / 32GB / 1TB',      true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='laptop')),
            (gen_random_uuid(), 'MON-27-4K',      '27 英寸 4K 显示器',                'monitor', 'EA', '27" 3840x2160 IPS / USB-C 90W PD / 菊花链',     true,  true, now(), now(), (SELECT id FROM procurement_categories WHERE code='monitor')),
            (gen_random_uuid(), 'SW-RHEL',        'Red Hat Enterprise Linux',          'os',      'LICENSE','RHEL Server Standard 1Y Subscription',        false, true, now(), now(), (SELECT id FROM procurement_categories WHERE code='os')),
            (gen_random_uuid(), 'SW-OFFICE365',   'Microsoft 365 E3',                  'saas',    'LICENSE','M365 E3 年度订阅 / 用户',                     false, true, now(), now(), (SELECT id FROM procurement_categories WHERE code='saas'))
        ON CONFLICT (code) DO NOTHING
    """)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM items WHERE code IN ('SRV-MEM-96GB','SRV-MEM-64GB','SRV-SSD-3.84T','SRV-SSD-1.92T','SRV-CPU-GOLD','SRV-GPU-H100','SRV-NIC-100G','NET-SW-48P','NET-FW-NGFW','NET-AP-WIFI7','LAPTOP-THINKPAD','MON-27-4K','SW-RHEL','SW-OFFICE365')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM procurement_categories WHERE code IN ('gpu','psu','switch','router','firewall','ap','os','db_license','saas','nas','san','tape','desktop','monitor','peripheral','storage','cloud','office','furniture')"
        )
    )
