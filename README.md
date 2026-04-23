<p align="center">
  <img src="frontend/src/assets/illustrations/otter-welcome.svg" width="120" alt="Mica Otter Mascot" />
</p>

<h1 align="center">Mica｜觅采</h1>

<p align="center">
  <strong>企业内部采购管理系统</strong><br />
  Internal Procurement Management System
</p>

<p align="center">
  <a href="https://github.com/helixzz/mica/releases/tag/v0.8.3"><img src="https://img.shields.io/badge/version-0.8.2-8B5E3C?style=flat-square" alt="Version" /></a>
  <a href="https://github.com/helixzz/mica/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/helixzz/mica/ci.yml?branch=main&style=flat-square&label=CI" alt="CI" /></a>
  <a href="https://codecov.io/gh/helixzz/mica"><img src="https://img.shields.io/codecov/c/github/helixzz/mica?style=flat-square&label=coverage" alt="Coverage" /></a>
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
需求提交 → 多级审批 → 询价比价(RFQ) → 采购订单 → 多批交货 → 分批付款 → 发票三单匹配
```

- **采购申请（PR）**：需求方只填物料和数量，价格由采购员询价后补充
- **多级审批 DSL**：按 `业务类型 + 金额区间` 自动路由多阶段串签 + 审批代理人
- **询价管理（RFQ）**：邀请多家供应商 → 在线录入报价 → 自动最低价定标
- **采购订单（PO）**：审批通过后一键生成，支持多批次交货 + 分批付款
- **合同管理**：全生命周期（归档 + OCR 全文检索 + 到期预警 + 分期付款计划）
- **发票核销**：AI 抽取（PDF / OFD / 图片 → LLM 结构化）+ 人工复核

### 📊 数据洞察

- **SKU 行情库**：90 天基准价 + ±20% 异常识别 + 多选价格走势对比图
- **采购分析**：供应商价格对比 · 采购历史 · 市场偏离率 · 波动率
- **角色化 Dashboard**：管理者看审批 + 趋势，采购员看待办 + 进度，需求方看自己的单

### 🔐 权限与安全

- **Cerbos 策略引擎**：字段级 + 行级细粒度权限，YAML 热加载
- **6 种角色**：管理员 / 采购经理 / 采购员 / 部门负责人 / 财务审核 / 需求方
- **审计日志**：全操作留痕，Admin 控制台可查

### 🌐 国际化 & 品牌

- **中 / 英双语**：持续双语同步，覆盖 SSO、管理员配置与表单填写引导场景
- **SAML SSO 基础能力**：管理员可在系统参数中配置 ADFS / 通用 SAML IdP，支持 SSO 登录、自动建用户与可选组映射
- **水獭棕品牌色系** `#8B5E3C`：浅色 / 暗色双主题 + 响应式布局 + 移动端适配
- **Inter + JetBrains Mono 字体**：专业阅读体验

## 技术栈

| 层 | 选型 |
|---|---|
| **后端** | Python 3.12 · FastAPI · SQLAlchemy 2.x (async) · Alembic |
| **前端** | React 18 · TypeScript 5 · Vite · Ant Design 5 · Zustand |
| **数据库** | PostgreSQL 16 · pg_trgm（中文全文检索） |
| **授权** | Cerbos sidecar（4 resource policies + graceful fallback） |
| **AI** | LiteLLM SDK（OpenAI / DeepSeek / GLM / 通义等兼容接口） |
| **国际化** | react-i18next（前端）· 自研消息字典（后端） |
| **测试** | pytest 264 tests · vitest 49 tests · GitHub Actions CI · Codecov |
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

> 密码统一为 `MicaDev2026!`　·　API 文档 http://localhost:8900/api/docs

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
├── backend/          Python 后端（FastAPI + SQLAlchemy + 12 migrations）
├── frontend/         React 前端（20+ 页面 · 602 i18n keys · 代码分割）
├── deploy/           Docker Compose + Nginx + Cerbos + 运维脚本
├── docs/             开发指南 · ADR · 用户手册（GitHub Pages）
└── .github/          CI 流水线（lint + test + coverage + docker build）
```

## 版本路线

| 版本 | 状态 | 主题 |
|---|---|---|
| v0.1 – v0.3 | ✅ | 基础设施 · 权限 · 审批 · 采购主线 |
| v0.4 | ✅ | LLM 接入 · 分批能力 · 管理员控制台 · SKU 行情库 |
| v0.5 | ✅ | UI 品牌化 · 通知中心 · 全局搜索 · 系统参数 · PDF/Excel 导出 · 运维脚手架 |
| v0.6 | ✅ | 测试 114 个 · 代码分割 -97% · Cerbos 授权 · 付款计划 · 采购分类体系 |
| **v0.7** | ✅ | **RFQ 询价 · Excel 导入 · 角色化 Dashboard · i18n 全覆盖 · 权限优化** |
| **v0.8** | ✅ | **覆盖率硬阈值 · PO 回填 SKU 价格库 · E2E CI 冒烟测试 · PR 分类 Bug 修复 · SAML SSO 基础能力 · 表单填写引导（第一波）** |
| v0.9 | 🚧 | 审批可视化编辑器 · 合同版本管理 · 更完整的表单引导覆盖 · 飞书集成（待 App ID） |

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
