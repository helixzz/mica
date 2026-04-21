# Changelog

All notable changes to Mica will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.5.0] — 2026-04-21

独立运行体验打磨：在不对接任何外部组件（飞书 / ADFS / 云账单）的前提下，把系统本身的功能完备性 + UI 体验打磨到生产可用水平。

### 新增

- **设计系统**：水獭棕 `#8B5E3C` 品牌色 10 级 + 冷暖灰中性 12 级 + 浅色 / 暗色双主题，系统偏好跟随 + 手动切换（localStorage 持久化）
- **UI 原语**：`PageHeader` / `StatCard` / `Section` / `EmptyState` 4 个可复用组件
- **水獭 SVG 插画**：`otter-empty` / `otter-search` / `otter-welcome`（`currentColor` 适配暗色）
- **响应式布局**：`AppLayout` 在 `lg` 断点切换到 Drawer 模式，移动端审批 / 查看流畅
- **通知系统**：`Notification` + `NotificationSubscription` 模型，审批 / 合同到期 / 价格异常自动推送
  - Header 铃铛 + 未读徽章 + 下拉抽屉
  - 独立通知中心页（Inbox + 订阅设置）
  - 审批任务分派时 → 推送给分派人；审批决定 → 推送给提交者
- **系统参数**：14 个硬编码阈值从代码搬到 DB，Admin 控制台"系统参数"Tab 可编辑
  - 涉及：审批金额、JWT/刷新令牌有效期、SKU 基准窗口 / 异常阈值、合同提醒窗口、上传限制、分页默认、审计回溯天数
  - 每个参数带 min/max 边界校验 + 单位 + 中英描述 + 重置到默认
- **统一全文搜索**：`GET /api/v1/search?q=&types=` 一个端点覆盖 7 张业务表
  - PR / PO / 合同 / 合同文档 / 发票 / 供应商 / 物料
  - pg_trgm + tsvector（`simple` 配置）+ GIN 索引
  - Header 全局搜索框（Cmd/Ctrl+K 聚焦，300ms 防抖，按类型分组结果）
  - 独立搜索结果页 `/search`
- **多级审批 DSL**：`ApprovalRule` 表按 `biz_type + 金额区间 + stages` 路由串签
  - 种子规则：`< ¥100k → dept_manager`（单阶段）· `≥ ¥100k → dept_manager → procurement_mgr`（两阶段串签）
  - 前一阶段通过后自动激活下一阶段；任一阶段拒绝后续阶段置 `skipped`
  - 管理员可 API / UI 增改规则
- **审批代理人**：`ApproverDelegation` 表支持出差临时委托
  - 时间段 + 原因 + 软撤销
  - 审批路由时自动检测活跃委托并转发任务
- **主数据 CRUD**：Supplier / Item / Company / Department 的增删改查
  - Department 支持 `parent_id` 树层级 + 循环检测
  - 每次写操作记入审计日志
  - Supplier/Item CUD 开放给 admin + procurement_mgr；Company/Department 仅 admin
- **PDF 导出（PO → 供应商签章版）**：`GET /api/v1/purchase-orders/{id}/export/pdf`
  - reportlab + STSong-Light CID 中文字体（无系统依赖）
  - 品牌色表头 + 斑马纹行项目 + 合计行 + 条款 + 签章位
- **Excel 导出（付款记录 → 财务）**：`GET /api/v1/payments/export/excel?po_id=&status_filter=`
  - openpyxl 生成 XLSX，冻结首行 + auto_filter + 合计行 + 品牌色样式
- **打印样式**：`@media print` 自动隐藏 Header / Sider / 按钮 / 分页，表格分断友好，链接附外部 URL
- **移动端响应式**：`@media (max-width: 576px)` StatCard 1 列 + 表格横滚 + 字号缩放 + Drawer 全屏 + 粘底操作栏
- **运维脚本**（`deploy/scripts/`）：
  - `health.sh` — 容器 / DB / API 健康检查（人读或 `--json`）
  - `backup.sh` — pg_dump + media tar 组合归档 + manifest.json
  - `restore.sh` — 双重确认的恢复（`--yes-i-know` + TTY `YES`）
  - `upgrade.sh` — 预检 → 备份 → 构建 → 迁移 → 健康检查（失败自动回滚）
  - `logs.sh` — `docker compose logs` 便捷包装

### 变更

- **用户手册配色**：mkdocs theme 从 `teal/orange` 改为 `brown/deep-orange` 对齐品牌
- **文档主题**：新增 `docs/user-manual/assets/mica.css` 精调水獭棕主色
- **字体**：前端全站使用 Inter（`@fontsource/inter` 自托管），代码字体 JetBrains Mono
- **Admin 控制台**：从 6 个 Tab 扩展到 7 个（新增"系统参数"）；原"系统参数"Tab 改名为"系统信息"
- **AppLayout**：Header 高度 56px，左有 Logo + 响应式菜单切换，中间搜索槽，右有通知铃铛 + 语言 + 主题切换 + 用户下拉

### 修复

- **Pydantic v2 递归类型**：`JSONValue` 从 `TypeAlias` 递归定义改为 `Any`，解决启动时 `RecursionError`
- **SQLAlchemy Enum 反序列化**：`SystemParameterCategory` + `NotificationCategory` 补齐 `values_callable=lambda e: [m.value for m in e]`，正确映射 DB 里的小写字符串

### 迁移

- `0002_notifications` — notifications + notification_subscriptions 表
- `0003_system_parameters` — 14 行 seed 业务参数
- `0004_fts_trigram` — 7 张表的 `search_vector` 生成列 + pg_trgm 扩展 + GIN 索引
- `0005_approval_rules_dsl` — approval_rules + approver_delegations 表 + 2 行 seed 规则 + `approval_tasks.meta` 列
- `0006_schema_additions` — `departments.parent_id` 与 `suppliers.notes` 列

### 依赖

- `reportlab>=4.2.5`（PDF 生成，含 STSong-Light CID 中文字体）
- `openpyxl>=3.1.5`（Excel 生成）
- `@fontsource/inter`（前端自托管 Inter 字体）
- `zustand`（轻量状态管理，用于通知 store）

### 文档

- 新增 [ADR 0002](docs/adr/0002-search-pg-trgm-over-zhparser.md)：全文检索选型决策
- 新增 [ADR 0003](docs/adr/0003-system-parameters.md)：系统参数集中配置决策
- 新增 [deploy/scripts/README.md](deploy/scripts/README.md)：运维脚本使用 + cron 示例 + 故障排查
- 新增 本 CHANGELOG

---

## [v0.4.2] — 2026-04-21（早些时候）

### 新增

- **SKU 行情库**：`GET /api/v1/sku/benchmarks/{item_id}` 返回 90 天基准价（avg / median / stddev / min / max / sample_size）
- **价格异常检测**：录入新价格时若偏离 ±20% 自动创建 `SKUPriceAnomaly` 记录（warning）或 ±40%（critical）
- **价格趋势**：`GET /api/v1/sku/trend/{item_id}` 返回近 180 天的价格点
- **合同附件**：PDF/OFD/XML/图片多格式上传，SHA-256 去重，一次性下载 token
- **合同 OCR 全文检索**：4 级分层抽取（PDF 结构化 / PDF OCR / OFD / LLM Vision）
- **合同到期提醒**：`GET /contracts-expiring?within_days=30`
- **发票详情页**：统一展示 PO 关联 / 产品行 / 金额 / 备注 / OCR 原文

### 修复

- 多处字段级权限边界修正

---

## [v0.4.1] — 2026-04（更早）

### 新增

- **管理员控制台前端**：LLM 模型 / AI 场景路由 / 用户管理 / AI 日志 / 审计日志 6 个 Tab（v0.5 新增第 7 个）
- **发票附件 + AI 抽取**：6 级分层策略（XML 99% 置信度 / PDF / OFD / 图片 OCR / LLM Vision 兜底 / 人工复核）

---

## [v0.4.0] — 2026-03

### 新增

- **LLM 网关**：LiteLLM SDK 接入，支持 OpenAI / DeepSeek / 通义 / 豆包 等多家模型
- **表单 AI 润色**：PR 标题 / 业务理由智能补全
- **字段级 + 行级权限**：按角色差异化可见字段 + 业务数据过滤

---

## [v0.3.0] — 2026-02

### 新增

- **审批引擎**：单级阈值路由（< ¥100k → 部门负责人；≥ ¥100k → 采购经理）
- **Walking Skeleton**：`docker compose up -d` 3 分钟启动端到端采购主线

---

## [v0.1.0 / v0.2.0] — 2025-12 ~ 2026-01

### 新增

- 采购申请 → 采购订单 → 合同 → 交货 → 付款 → 发票 的完整业务主线骨架
- 多公司主体 + 多币种预留
- 中英双语 i18n 框架
- PostgreSQL + SQLAlchemy 2 async + Alembic 迁移基础设施
- Docker Compose v2 + Nginx 部署骨架

---

## 版本路线（规划中）

### v0.6（下一迭代）

- 飞书集成（消息通知 + 审批卡片联动，需 App ID/Secret）
- 单元测试覆盖 + GitHub Actions CI 流水线
- 真实 LLM 模型接通演示
- 批量导入 Excel（供应商 / 物料 / 历史报价）

### v0.7+

- Cerbos sidecar 化（字段级 authz 独立为策略引擎）
- PostgreSQL zhparser 中文分词（升级当前 pg_trgm 方案）
- PO 成交价自动回填 SKU 价格库
- 多级审批 DSL 可视化编辑器
- 合同版本管理 / 电子签 / 续签流

### 按需

- ADFS SAML 真实对接（骨架已就绪）
- 云服务商账单自动生成月度 PO
- 前端 bundle 代码分割

---

**最后更新**：2026-04-21 · **维护人**：helixzz
