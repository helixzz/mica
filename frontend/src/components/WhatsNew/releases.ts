/**
 * What's new — the human-readable version history.
 *
 * Kept as data rather than i18n keys: this list grows with every release and
 * would bloat common.json. Each entry carries its own zh/en text, chosen at
 * render time from the active language.
 *
 * Write these from the *user's* point of view — what they can now do, in words
 * they would use. Migrations, tests and refactors belong in CHANGELOG.md.
 */
export type ReleaseKind = 'new' | 'fix' | 'improvement'

export interface ReleaseItem {
  kind: ReleaseKind
  zh: string
  en: string
}

export interface Release {
  version: string
  date: string
  items: ReleaseItem[]
}

export const RELEASES: Release[] = [
  {
    version: '1.63.0',
    date: '2026-10-20',
    items: [
      {
        kind: 'new',
        zh: '执行付款时可选「先票」或「后票」，默认沿用该供应商的常见做法，单笔可改',
        en: 'Choose invoice-first or invoice-later when executing a payment — prefilled from the supplier, changeable per payment',
      },
      {
        kind: 'new',
        zh: '选「先票」必须当场上传发票，发票自动归档到发票页面',
        en: 'Invoice-first requires uploading the invoice right there; it is filed on the invoice page automatically',
      },
      {
        kind: 'new',
        zh: '「后票」会在付款记录里标出待补票和剩余天数，超期标红，可就地补传',
        en: 'Invoice-later shows as owed in the payment list with days remaining, turns red when overdue, and can be completed there',
      },
    ],
  },
  {
    version: '1.62.1',
    date: '2026-10-20',
    items: [
      {
        kind: 'improvement',
        zh: '合同扫描件压缩默认提高到 200 dpi，文字更清楚（仍省约 87%）',
        en: 'Contract scans now compress at 200 dpi — crisper text, still ~87% smaller',
      },
      {
        kind: 'fix',
        zh: '压缩绝不把合同转成灰度（红章会丢色）',
        en: 'Compression never turns a contract grayscale (red seals would lose their colour)',
      },
    ],
  },
  {
    version: '1.62.0',
    date: '2026-10-20',
    items: [
      {
        kind: 'new',
        zh: '上传上限提到 50 MB，扫描件自动压缩后再存',
        en: 'Uploads up to 50 MB; scans are compressed before being stored',
      },
    ],
  },
  {
    version: '1.61.0',
    date: '2026-10-20',
    items: [
      {
        kind: 'new',
        zh: '合同详情显示我司采购主体，签约方一眼可辨',
        en: 'The contract page now shows which of our companies signs it',
      },
      {
        kind: 'new',
        zh: '顶栏新增「更新」按钮，可以随时回看每次版本变化',
        en: 'A What\'s new button in the header keeps the release history at hand',
      },
    ],
  },
  {
    version: '1.60.1',
    date: '2026-10-20',
    items: [
      {
        kind: 'fix',
        zh: '修复确认收货时必定报错的问题（此前收货功能实际不可用）',
        en: 'Fixed receiving always failing with an error (the feature was unusable)',
      },
      {
        kind: 'new',
        zh: '订单页显示我司采购主体',
        en: 'The order page shows our purchasing entity',
      },
    ],
  },
  {
    version: '1.60.0',
    date: '2026-10-20',
    items: [
      {
        kind: 'new',
        zh: '付款计划支持常用模板：预付 100%、验收尾款 100%、预付 30% + 尾款 70%、预付 50% + 尾款 50%，一键填好期次',
        en: 'Payment schedule templates: advance 100%, acceptance 100%, 30% + 70%, 50% + 50% — installments filled in one click',
      },
      {
        kind: 'new',
        zh: '付款计划旁显示订单收货进度，付款前先看货到没到',
        en: 'The payment schedule shows how much of the order has been received',
      },
      {
        kind: 'improvement',
        zh: '新建供应商时编码留空即可自动生成，不必再手工排队',
        en: 'Supplier codes are generated automatically when left empty',
      },
    ],
  },
  {
    version: '1.59.0',
    date: '2026-10-20',
    items: [
      {
        kind: 'new',
        zh: '发货与收货拆成两步：订单状态变为 待发货 → 已发货 → 部分收货 → 已完成',
        en: 'Shipping and receiving are separate now: awaiting shipment → shipped → partially received → completed',
      },
      {
        kind: 'new',
        zh: '订单详情新增「收货」页签，申请人可登记实收数量，支持分批多次收货与撤销',
        en: 'New Receipts tab on the order: record what actually arrived, in as many passes as needed, and revoke a mistake',
      },
      {
        kind: 'new',
        zh: '登记或撤销收货会通知订单相关人',
        en: 'Recording or revoking a receipt notifies the people on the order',
      },
    ],
  },
  {
    version: '1.58.3',
    date: '2026-10-20',
    items: [
      {
        kind: 'fix',
        zh: '修复交货批次的到货数量改不了、删掉重建会算出 200% 到货的问题',
        en: 'Fixed batch quantities that could not be corrected and recomputed to 200% received',
      },
      {
        kind: 'fix',
        zh: '采购申请详情页的审批按钮恢复可用',
        en: 'Approval actions on the requisition page work again',
      },
    ],
  },
]
