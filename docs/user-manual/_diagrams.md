# Mica 流程图集

本文件集中存放《Mica 用户手册》所需的全部 Mermaid 流程图，供其它章节 include/引用。所有图均可在 GitHub 上原生渲染，无需外部图片资源。

图中节点文字以中文为主，首次出现的关键术语后附英文缩写，如"采购申请 (PR)"。版本基线：Mica v0.4（单级审批、发票 `draft → verified → approved → paid` 链路）。

---

## 1. 全局业务主线

该图展示 Mica 的端到端采购主线：从 **IT 采购员** 发起采购申请，经 **部门负责人 / 采购经理** 审批后生成采购订单，再依次产生合同、多批次交货、发票与付款。两条虚线分支分别表示审批被拒绝或退回后的回退路径。

```mermaid
flowchart LR
    A[IT 采购员<br/>发起采购申请 PR] --> B{审批}
    B -- 通过 --> C[生成采购订单 PO]
    B -- 退回 --> A
    B -- 拒绝 --> X((流程终止))
    C --> D[签订合同<br/>Contract]
    D --> E[多批次交货<br/>Shipment Batch 1..N]
    E --> F[登记发票<br/>Invoice]
    F --> G[登记付款<br/>Payment]
    G --> H((订单关闭<br/>PO Closed))

    classDef terminal fill:#f5f5f5,stroke:#999,color:#666;
    class X,H terminal;
```

---

## 2. 采购申请（PR）状态机

对应后端 `PRStatus` 枚举（见 `backend/app/models/__init__.py:34-41`）。一个 PR 从草稿起步，提交后进入待审批，审批人可做出三种决定；被退回后可回到草稿再次修改、再次提交；审批通过的 PR 在生成 PO 后进入终态 `converted`。

```mermaid
stateDiagram-v2
    [*] --> draft: 新建申请
    draft --> submitted: 提交审批<br/>(submit_pr)
    draft --> cancelled: 取消
    submitted --> approved: 审批通过<br/>(decide approve)
    submitted --> rejected: 审批拒绝<br/>(decide reject)
    submitted --> returned: 审批退回<br/>(decide return)
    returned --> draft: 修改后重新编辑
    approved --> converted: 生成采购订单<br/>(convert_pr_to_po)
    approved --> cancelled: 取消（特殊情况）

    rejected --> [*]
    cancelled --> [*]
    converted --> [*]
```

---

## 3. 采购订单（PO）状态机

对应后端 `POStatus` 枚举（`backend/app/models/__init__.py:44-50`）。PO 由审批通过的 PR 转换而来，默认进入 `confirmed`；随着交货批次陆续验收，状态在 `partially_received` 与 `fully_received` 间流转，最终可关闭归档。

```mermaid
stateDiagram-v2
    [*] --> draft: 极少使用
    draft --> confirmed: PR 转换生成 PO
    [*] --> confirmed: PR 转换生成 PO（常规路径）
    confirmed --> partially_received: 首批到货验收
    partially_received --> partially_received: 后续批次到货
    partially_received --> fully_received: 全部到货验收完毕
    confirmed --> fully_received: 一次性全量到货
    fully_received --> closed: 订单关闭<br/>（付款 & 开票完结）
    confirmed --> cancelled: 整单取消
    partially_received --> cancelled: 中止后续批次

    closed --> [*]
    cancelled --> [*]
```

---

## 4. 发票（Invoice）状态机 — 当前实现

v0.4 当前链路：发票创建即进入 `verified`（见 `backend/app/services/flow.py:398`，系统自动核对行项与 PO），随后财务审核员审批，审批通过后登记付款，付款确认后发票转为 `paid`。**注**：模型枚举中已预留 `pending_match / matched / mismatched`，计划在下一迭代改造为三单匹配链路，当前手册仅描述现行实现。

```mermaid
stateDiagram-v2
    [*] --> draft: 保存草稿（极少使用）
    [*] --> verified: 创建发票<br/>（与 PO 行自动核对）
    draft --> verified: 提交核对
    verified --> approved: 财务审核通过
    verified --> cancelled: 作废
    approved --> paid: 付款完成
    approved --> cancelled: 作废
    paid --> [*]
    cancelled --> [*]
```

---

## 5. IT 采购员日常工作流

IT 采购员是系统的主要发起人。典型动作：登录 → 在仪表盘新建 PR → 调用 AI 润色业务说明 → 逐行录入明细 → 提交审批 → 等审批通过 → 一键转 PO → 登记到货批次。

```mermaid
flowchart TD
    S[登录 Mica] --> D[打开仪表盘<br/>Dashboard]
    D --> N[新建采购申请 PR]
    N --> T[填写标题 / 所需日期 / 币种]
    T --> AI{使用 AI 润色<br/>业务说明?}
    AI -- 是 --> AIC[调用 AI 润色<br/>ai_polish]
    AIC --> L[录入明细行<br/>物料 / 数量 / 单价 / 供应商]
    AI -- 否 --> L
    L --> SUB[提交审批]
    SUB --> W[等待审批结果]
    W --> R{审批结论}
    R -- 已批准 --> CV[一键生成<br/>采购订单 PO]
    R -- 已退回 --> T
    R -- 已拒绝 --> END((流程结束))
    CV --> SH[录入交货批次<br/>Shipment]
    SH --> RCV[确认验收到货]
    RCV --> DONE((交付完成))

    classDef terminal fill:#f5f5f5,stroke:#999,color:#666;
    class END,DONE terminal;
```

---

## 6. 部门负责人审批工作流

部门负责人的核心动作是在仪表盘查看本部门的待办审批（对应 `approval_tasks` 表中 `assignee_id=本人 AND status=pending` 的条目），逐条审阅 PR 明细后做出决定。金额 ≥ 10 万 的申请会自动路由给采购经理，不会出现在部门负责人的待办里。

```mermaid
flowchart TD
    S[登录 Mica] --> D[打开仪表盘<br/>Dashboard]
    D --> TODO[查看待办审批<br/>approval_tasks = pending]
    TODO --> E{有待办?}
    E -- 无 --> IDLE((暂无任务))
    E -- 有 --> O[打开 PR 详情]
    O --> RD[查看申请说明<br/>+ 明细行 + 金额]
    RD --> C[填写审批意见<br/>（可选）]
    C --> DEC{审批决定}
    DEC -- 批准 --> AP[approve<br/>PR → approved]
    DEC -- 退回 --> RT[return<br/>PR → returned<br/>回到申请人]
    DEC -- 拒绝 --> RJ[reject<br/>PR → rejected<br/>流程终止]
    AP --> TODO
    RT --> TODO
    RJ --> TODO

    classDef terminal fill:#f5f5f5,stroke:#999,color:#666;
    class IDLE terminal;
```

---

## 7. 财务审核员工作流

财务审核员在 PO 全部到货后进入：核对 PO → 登记发票（自动与 PO 行核对进入 `verified`）→ 审核发票（转 `approved`）→ 登记付款（`pending`）→ 确认付款（付款记录转 `confirmed`、发票转 `paid`）。

```mermaid
flowchart TD
    S[登录 Mica] --> POL[打开 PO 列表]
    POL --> PICK[选择已到货的 PO]
    PICK --> VIEW[查看到货/开票/付款进度]
    VIEW --> INV[登记发票<br/>create_invoice]
    INV --> V[发票状态=verified<br/>自动与 PO 行核对]
    V --> APR[审核通过<br/>发票状态=approved]
    APR --> PAY[登记付款<br/>payment 状态=pending]
    PAY --> CONF[确认付款到账]
    CONF --> CF[付款=confirmed<br/>发票=paid]
    CF --> CHK{该 PO 全部付清?}
    CHK -- 是 --> CLOSE[PO → closed]
    CHK -- 否 --> POL
    CLOSE --> DONE((流程结束))

    classDef terminal fill:#f5f5f5,stroke:#999,color:#666;
    class DONE terminal;
```

---

## 8. 时序图：提交 PR 到生成 PO

完整描述一次"发起 → 审批 → 转单"过程中前后端、审批引擎与两位用户（申请人 Alice、审批人 Bob）之间的交互。审批引擎内部按 `_resolve_approver` 规则解析审批人：`金额 ≥ 100000` 优先路由到采购经理（`procurement_mgr`），否则路由到同部门的 `dept_manager`，都找不到则兜底给 `admin`（见 `backend/app/services/approval.py:20-46`）。

```mermaid
sequenceDiagram
    autonumber
    actor Alice as Alice<br/>(IT 采购员)
    participant FE as 前端 (React)
    participant BE as 后端 API<br/>(FastAPI)
    participant AP as 审批引擎<br/>(approval_svc)
    participant DB as 数据库<br/>(approval_instances /<br/>approval_tasks)
    actor Bob as Bob<br/>(部门负责人/采购经理)

    Alice->>FE: 填写 PR 并点击"提交审批"
    FE->>BE: POST /api/prs/{id}/submit
    BE->>BE: submit_pr()<br/>PR.status = submitted
    BE->>AP: create_instance_for_pr(amount)
    AP->>AP: _resolve_approver<br/>金额 ≥ 10 万 → 采购经理<br/>否则 → 同部门负责人
    AP->>DB: INSERT approval_instance<br/>+ approval_task(assignee=Bob)
    AP-->>BE: instance
    BE-->>FE: 200 OK { pr, approval }
    FE-->>Alice: 显示"已提交，等待审批"

    Note over Bob,FE: Bob 登录后在仪表盘看到待办
    Bob->>FE: 打开待办 → 点击"批准"
    FE->>BE: POST /api/prs/{id}/decide<br/>{action: "approve", comment}
    BE->>AP: act_on_task(user=Bob, approve)
    AP->>DB: UPDATE task.status=approved<br/>UPDATE instance.status=approved
    BE->>BE: decide_pr()<br/>PR.status = approved
    BE-->>FE: 200 OK
    FE-->>Bob: 显示"审批通过"

    Note over Alice,FE: Alice 刷新后看到 PR 已批准
    Alice->>FE: 点击"生成采购订单"
    FE->>BE: POST /api/prs/{id}/convert
    BE->>BE: convert_pr_to_po()<br/>PR.status = converted<br/>INSERT purchase_order + po_items
    BE-->>FE: 200 OK { po_number: PO-2026-0001 }
    FE-->>Alice: 跳转到 PO 详情
```

---

## 9. 权限三层防御

Mica 对每次 HTTP 请求实施三层防御（概念示意，当前 v0.4 以应用层实现为主，Cerbos / Postgres RLS 作为后续版本的兜底通道）。任何一层放行失败即终止请求。

```mermaid
flowchart LR
    REQ[HTTP 请求<br/>带 Authorization 头] --> L1[第 1 层<br/>JWT 身份验证<br/>Depends: get_current_user]
    L1 -- 通过 --> L2[第 2 层<br/>行级角色过滤<br/>按 role/company/dept<br/>裁剪查询结果]
    L1 -- 失败 --> R401((401<br/>未登录))
    L2 -- 通过 --> L3[第 3 层<br/>字段级裁剪<br/>按角色隐藏敏感字段<br/>如价格/税号]
    L2 -- 拒绝 --> R403((403<br/>insufficient_role))
    L3 --> OK((200 OK<br/>返回最小可见数据))

    classDef deny fill:#fff0f0,stroke:#c33,color:#c33;
    class R401,R403 deny;
    classDef pass fill:#f0fff0,stroke:#393,color:#393;
    class OK pass;
```

---

## 10. i18n 语言检测流程

前端在首次加载时按优先级链判定用户使用的语言，命中即止。一旦用户在界面上手动切换，新的选择会被写入 `localStorage`，后续访问直接命中第 1 步。

```mermaid
flowchart TD
    START[页面首次加载] --> S1{localStorage<br/>mica_locale 存在?}
    S1 -- 是 --> USE[使用该语言]
    S1 -- 否 --> S2{Cookie<br/>mica_locale 存在?}
    S2 -- 是 --> USE
    S2 -- 否 --> S3{navigator.language<br/>可识别?}
    S3 -- 是 --> M[映射到<br/>zh-CN / en-US]
    M --> USE
    S3 -- 否 --> S4{HTTP 请求<br/>Accept-Language?}
    S4 -- 是 --> M
    S4 -- 否 --> DEF[回退到默认<br/>zh-CN]
    DEF --> USE
    USE --> APP[加载对应语言包<br/>react-i18next]
    APP --> UI((渲染界面))

    USER[用户点击<br/>语言切换器] --> SAVE[写入 localStorage<br/>mica_locale]
    SAVE --> RELOAD[刷新语言包]
    RELOAD --> UI
```

---

## 图索引

| 编号 | 图标题 | 类型 | 主要角色 / 对象 | 推荐引用章节 |
|----|------|----|---------------|----------|
| 1 | 全局业务主线 | flowchart LR | IT 采购员 / 审批人 / 财务审核 | 概述 · 业务全景 |
| 2 | 采购申请（PR）状态机 | stateDiagram-v2 | PR 对象 | 采购申请 · 状态说明 |
| 3 | 采购订单（PO）状态机 | stateDiagram-v2 | PO 对象 | 采购订单 · 状态说明 |
| 4 | 发票（Invoice）状态机 — 当前实现 | stateDiagram-v2 | Invoice 对象 | 发票与付款 · 当前实现 |
| 5 | IT 采购员日常工作流 | flowchart TD | IT 采购员 | 角色指南 · IT 采购员 |
| 6 | 部门负责人审批工作流 | flowchart TD | 部门负责人 / 采购经理 | 角色指南 · 审批人 |
| 7 | 财务审核员工作流 | flowchart TD | 财务审核 | 角色指南 · 财务审核 |
| 8 | 时序图：提交 PR 到生成 PO | sequenceDiagram | Alice（申请人）/ Bob（审批人）/ 系统 | 端到端示例 |
| 9 | 权限三层防御 | flowchart LR | 系统架构 | 附录 · 安全模型 |
| 10 | i18n 语言检测流程 | flowchart TD | 前端 / 用户 | 附录 · 多语言 |

---

> **维护约定**
> - 所有状态名、角色名应与 `backend/app/models/__init__.py` 中的枚举及 `frontend/src/i18n/locales/zh-CN/common.json` 中的文案保持一致。
> - 升级链路（如发票改为 `pending_match / matched / mismatched`）时，新增新版图并在此图索引追加一行，旧图标注"历史版本"而非直接删除，以便回溯既有手册。
