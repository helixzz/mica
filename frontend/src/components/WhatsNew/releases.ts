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
    version: '1.67.0',
    date: '2026-10-21',
    items: [
      {
        kind: 'fix',
        zh: '采购订单的付款计划现在也能选先票/后票（此前只有合同的付款计划有这个选项）',
        en: 'Payment schedules on purchase orders now offer invoice-first / invoice-later too, not just contracts',
      },
      {
        kind: 'improvement',
        zh: '新增付款执行回归测试，先票上传发票并归档的流程每次发版都会自动跑一遍',
        en: 'A regression test now covers invoice-first payment execution on every release',
      },
    ],
  },
  {
    version: '1.66.1',
    date: '2026-10-21',
    items: [
      {
        kind: 'improvement',
        zh: '回归测试更可靠：全量 56 项端到端用例串行执行，登录竞态不再造成假失败',
        en: 'More reliable regression: all 56 end-to-end cases run serially, so login races no longer cause false failures',
      },
    ],
  },
  {
    version: '1.66.0',
    date: '2026-10-21',
    items: [
      {
        kind: 'new',
        zh: '仪表盘新增「待取回询价单」卡片：哪些已发出、还有几家没回、哪些已逾期',
        en: 'New dashboard card for quotations awaiting collection — who has not replied, what is overdue',
      },
    ],
  },
  {
    version: '1.65.2',
    date: '2026-10-21',
    items: [
      {
        kind: 'new',
        zh: '询价单列表顶部显示「待取回」提醒：哪些已发出、还有几家没回、哪些已过截止日',
        en: 'The RFQ list flags quotations awaiting collection — who has not replied, and what is past deadline',
      },
    ],
  },
  {
    version: '1.65.1',
    date: '2026-10-21',
    items: [
      {
        kind: 'fix',
        zh: '补齐更新日志：此前只显示到 v1.63.0，后面六个版本的变更都漏了',
        en: 'The release history now covers v1.63.1 through v1.65.0, which had been missing',
      },
    ],
  },
  {
    version: '1.65.0',
    date: '2026-10-21',
    items: [
      {
        kind: 'new',
        zh: '询价单改按采购的模板生成：表头与明细自动填好，单价/税率/交期/质保留空给供应商',
        en: 'Quotation sheets now follow the procurement template — header and lines filled, prices left for the supplier',
      },
      {
        kind: 'improvement',
        zh: '明细行按实际物料数生成，合计公式自动覆盖所有行；物料少时保留空行供供应商多报',
        en: 'Line rows match the actual item count, totals cover every row, and short RFQs keep blank rows to spare',
      },
    ],
  },
  {
    version: '1.64.1',
    date: '2026-10-21',
    items: [
      {
        kind: 'improvement',
        zh: '付款预测图也能切换币种，图表和金额符号一起变',
        en: 'The payment forecast chart can switch currency too, chart and symbols together',
      },
    ],
  },
  {
    version: '1.64.0',
    date: '2026-10-21',
    items: [
      {
        kind: 'fix',
        zh: '现金流预测与付款预测不再把不同币种的钱加在一起（此前港币被当成人民币算）',
        en: 'Cash-flow and payment forecasts no longer add different currencies together',
      },
      {
        kind: 'new',
        zh: '两个预测面板支持按币种查看',
        en: 'Both forecast panels can be viewed per currency',
      },
      {
        kind: 'improvement',
        zh: '注意：预测合计会变小——它不再包含其他币种的金额，此前那个数字是虚高的',
        en: 'Note: forecast totals get smaller — they no longer include other currencies',
      },
    ],
  },
  {
    version: '1.63.3',
    date: '2026-10-20',
    items: [
      {
        kind: 'fix',
        zh: '新建合同时金额前缀不再固定显示人民币，港币合同会正确显示 HK$',
        en: 'The contract amount field no longer always shows ¥, so HKD contracts read correctly',
      },
    ],
  },
  {
    version: '1.63.2',
    date: '2026-10-20',
    items: [
      {
        kind: 'fix',
        zh: '修复在合同付款计划上执行"先票"时报「缺少供应商信息」、无法归档发票的问题',
        en: 'Fixed invoice-first payments on contract schedules failing with a missing-supplier error',
      },
    ],
  },
  {
    version: '1.63.1',
    date: '2026-10-20',
    items: [
      {
        kind: 'fix',
        zh: '飞书回调改为强制校验签名（此前不携带签名头即可绕过）',
        en: 'Feishu callbacks now always verify the signature',
      },
    ],
  },
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
