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
