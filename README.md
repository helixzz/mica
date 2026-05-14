<p align="center">
  <img src="frontend/src/assets/illustrations/otter-welcome.svg" width="120" alt="Mica Otter Mascot" />
</p>

<h1 align="center">Mica｜觅采</h1>

<p align="center">
  <strong>企业内部采购管理系统</strong><br />
  Internal Procurement Management System
</p>

<p align="center">
  <a href="https://github.com/helixzz/mica/releases/tag/v1.9.3"><img src="https://img.shields.io/badge/version-1.9.3-8B5E3C?style=flat-square" alt="Version" /></a>
  <a href="https://github.com/helixzz/mica/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/helixzz/mica/ci.yml?branch=main&style=flat-square&label=CI" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" alt="License" /></a>
  <img src="https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/react-18-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
</p>

<p align="center">
  <a href="docs/QUICKSTART.md">快速开始</a> ·
  <a href="https://helixzz.github.io/mica/">用户手册</a> ·
  <a href="docs/DEVELOPMENT.md">开发指南</a> ·
  <a href="CHANGELOG.md">更新日志</a> ·
  <a href="docs/adr/">架构决策</a>
</p>

---

## 设计理念

> **效率优先 > 扩展性 > 标准化管控** — 系统服务于人，而不是限制人。

面向 IT 部门（< 100 人、月 < 300 单）的轻量采购管理，从"提需求"到"付款核销"全链条覆盖，无需部署 SAP / Oracle 等重型 ERP。

## 核心功能

### 🛒 采购全流程

```
需求提交 → 多级审批 → 询价比价 (RFQ) → 采购订单 → 多批交货 → 分批付款 → 发票三单匹配
```

- **采购申请（PR）**：需求方只填物料和数量，价格由采购员询价后补充
- **多级审批 DSL**：按 `业务类型 + 金额区间` 自动路由多阶段串签，支持审批代理人
- **询价管理（RFQ）**：创建询价单 → 邀请供应商 → 在线报价 → 自动/手动定标
- **采购订单（PO）**：审批通过后一键生成，自动带入 PR 标题便于识别
- **合同管理**：全生命周期（归档 + OCR AI 提取 + 到期预警 + 分期付款计划 + 版本历史）
- **交货计划**：PO / 合同附属，支持批量创建、进度可视化、与到货批次关联
- **分批到货**：多批次登记，支持计划日期与实际日期、承运商、物流单号
- **分批付款**：按交货进度分期付款，合同付款计划自动核销
- **发票核销**：AI 抽取（PDF / OFD / 图片 → LLM 结构化）+ 三单匹配

### 📢 通知与调度

- **飞书卡片推送**：31 个业务事件自动触发，结构化 Markdown 卡片（含 PR 标题、物料、金额、操作人等）
- **消息通知中心**：WebSocket 实时推送，应用内通知 + 飞书 + 邮件三通道
- **可配置开关**：Admin → 系统参数中 15 个独立 toggle，可关闭任一事件的通知
- **内置调度器**：mica-scheduler 服务自动执行（每日摘要 09:00、审批提醒每小时、SLA 升级 30 分钟、合同到期预警 10:00）
- **审计日志**：所有通知事件（创建/发送成功/发送失败）完整记录

### 📊 数据洞察

- **角色化 Dashboard**：拖拽排序，管理者看审批 + 趋势，采购员看待办 + 进度，需求方看自己的单
- **SKU 行情库**：90 天基准价 + 价格异常识别 + 趋势预测（7 日/30 日均价）
- **采购分析**：支出趋势、部门消费排行、供应商交期表现
- **发票匹配状态**：Dashboard 展示 PO 订单量/到货量/开票量匹配

### 🔐 权限与安全

- **Cerbos 策略引擎**：字段级 + 行级细粒度权限，YAML 热加载，不可达时自动降级
- **6 种角色**：管理员 / 采购经理 / 采购员 / 部门负责人 / 财务审核 / 需求方
- **审计日志**：全操作留痕，Admin 控制台可查
- **供应商门户**：token 只读访问（PO / 合同 / 付款 / 到货），90 天自动过期 + 限流

### 🌐 国际化 & 品牌

- **中 / 英双语**：前端 1184 keys parity、后端 244 keys parity
- **SAML SSO**：ADFS / 通用 SAML IdP，JIT 自动建用户 + 可选的组映射
- **水獭棕品牌色系** `#8B5E3C`：浅色 / 暗色双主题 + 响应式布局 + 移动端适配
- **Inter + JetBrains Mono 字体**：专业阅读体验

## 技术栈

| 层 | 选型 |
|---|---|
| **后端** | Python 3.12 · FastAPI · SQLAlchemy 2.x (async) · Alembic (43 migrations) |
| **前端** | React 18 · TypeScript 5 · Vite · Ant Design 5 · Zustand · react-i18next |
| **数据库** | PostgreSQL 16 · pg_trgm（中文全文检索） |
| **授权** | Cerbos sidecar（4 resource policies + graceful fallback） |
| **AI** | LiteLLM SDK（OpenAI / DeepSeek / GLM / 通义等兼容接口） |
| **定时任务** | APScheduler (AsyncIOScheduler)，4 个 cron 任务 |
| **推送** | 飞书卡片消息 · SMTP 邮件 · WebSocket |
| **测试** | pytest · vitest · Playwright E2E · GitHub Actions CI |
| **部署** | Docker Compose v2 · Nginx · 一键脚本（备份/恢复/升级/健康检查） |

## 快速开始

```bash
git clone https://github.com/helixzz/mica.git
cd mica/deploy
./scripts/dev-up.sh          # 首次约 90 秒（构建镜像 + 迁移 + seed）
```

访问 <http://localhost:8900>（本机）或 `http://<LAN-IP>:8900`（局域网）。

| 账号 | 角色 | 用途 |
|---|---|---|
| `admin` | 管理员 | 系统配置、全局视图 |
| `alice` | IT 采购员 | 提单、询价、下单 |
| `bob` | 部门负责人 | 审批 |
| `carol` | 财务审核 | 付款、发票核销 |
| `dave` | 采购经理 | 大额审批、供应商管理 |

> 密码统一为 `MicaDev2026!` · API 文档 <http://localhost:8900/api/docs>

## 运维脚本

```bash
cd deploy
./scripts/health.sh              # 健康检查（表格或 --json）
./scripts/backup.sh              # 备份 DB + media
./scripts/restore.sh <archive>   # 从归档恢复
./scripts/upgrade.sh             # 升级（备份 → 构建 → 迁移 → 健康检查，失败自动回滚）
./scripts/logs.sh backend        # 查看容器日志
```

详见 [deploy/scripts/README.md](deploy/scripts/README.md)。

## 项目结构

```
mica/
├── backend/
│   ├── app/
│   │   ├── api/v1/           REST 端点（20+ 路由文件）
│   │   ├── services/         业务逻辑（审批、合同、RFQ、通知、摘要等）
│   │   ├── core/             安全、授权、i18n、Cerbos 客户端
│   │   ├── models/           所有 ORM 模型（单文件 ~1500 行）
│   │   ├── schemas/          Pydantic 请求/响应模型
│   │   └── i18n/messages/    zh-CN.json + en-US.json
│   └── migrations/versions/  43+ Alembic 迁移文件
├── frontend/
│   └── src/
│       ├── pages/             30+ 页面（含 admin 子面板）
│       ├── components/        可复用 UI 组件
│       ├── api/               axios 封装 + API 定义
│       ├── i18n/locales/      zh-CN + en-US (1184 keys)
│       └── stores/            Zustand 状态管理
├── deploy/                    Docker Compose + Nginx + Cerbos + 运维脚本
├── docs/                      开发指南 · ADR · 用户手册（GitHub Pages）
└── .github/                   CI 流水线（lint + test + coverage + docker build）
```

## 版本路线

| 版本 | 状态 | 主题 |
|---|---|---|
| v0.1 – v0.6 | ✅ | 基础设施 · 权限 · 审批 · PR/PO 主线 · LLM · Dashboard · 通知 · 品牌化 |
| v0.7 | ✅ | RFQ 框架 · 角色化 Dashboard · i18n 审计 · 采购分类 |
| v0.8 | ✅ | 覆盖率 · SAML SSO · E2E 测试 · 表单引导 |
| v0.9 – v1.5 | ✅ | 审批编辑器 · 合同版本 · 供应商管理 · 搜索增强 · 批量导入 |
| v1.6 – v1.7 | ✅ | Cerbos · 付款计划 · 飞书集成 · 合同 OCR · 交货计划 · SLA · 邮件摘要 |
| **v1.8** | ✅ | **RFQ 完整 · 通知系统 · 调度器 · 发票匹配 · SKU 预测 · 供应商门户 · Dashboard 重构** |
| v1.9 | 🚧 | 飞书审批卡片联动 · E2E 浏览器测试增强 · 更多文档 |

> 完整变更记录见 [CHANGELOG.md](CHANGELOG.md) · 所有 Release 见 [GitHub Releases](https://github.com/helixzz/mica/releases)

## 文档

| 文档 | 说明 |
|---|---|
| [用户手册](https://helixzz.github.io/mica/) | 业务操作指南（GitHub Pages） |
| [Quickstart](docs/QUICKSTART.md) | 3 分钟启动 |
| [开发指南](docs/DEVELOPMENT.md) | 添加 API / 参数 / 审批规则 / 通知类型 |
| [ADR](docs/adr/) | 架构决策记录（技术栈 · 搜索选型 · 系统参数） |
| [运维手册](deploy/scripts/README.md) | 脚本用法 · cron 示例 · 故障排查 |

## 许可

[Apache License 2.0](LICENSE) — 详见 [NOTICE](NOTICE)。

## 致谢

- 水獭吉祥物 & 插画 — 内部原创
- 字体 — [Inter](https://rsms.me/inter/)（OFL）· [JetBrains Mono](https://www.jetbrains.com/lp/mono/)（OFL）
- PDF 中文字体 — Adobe STSong-Light CID（reportlab 内置）