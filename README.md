# Mica｜觅采

企业内部采购管理系统 — 服务 IT 部门为主，渐进扩展至其他部门。

- **中文名**：觅采
- **英文名**：Mica
- **定位**：企业内部采购管理系统（Internal Procurement Management System）
- **状态**：✅ v0.6.0 — 测试基础设施 + 质量工程 + Cerbos 授权（2026-04-22）

---

## 设计理念

> **效率优先 > 扩展性 > 标准化管控**
> 系统服务于人，而不是限制人。

## 已交付能力（v0.5.0）

### 采购主线（v0.1 - v0.4）
- 多公司主体 + 多币种
- 中文 / 英文双语（浏览器自动检测 + 用户手动切换）
- 采购申请 → 审批 → 订单 → 多批次交货 → 分批付款 → 发票三单匹配
- 字段级 + 行级细粒度权限（单级审批 → v0.5 多级串签 + 代理人）
- 合同全生命周期（归档 + OCR 全文检索 + 到期提醒）
- SKU 行情库（90 天基准价 + ±20% 异常识别 + 趋势回看）
- 发票 AI 抽取（PDF/OFD/图片 → LLM 结构化 → 人工复核）

### v0.5 新增
- **现代化 UI**：水獭棕 `#8B5E3C` 品牌色系 + 浅色 / 暗色双主题 + 响应式布局（支持移动端审批）
- **通知中心**：审批 / 合同到期 / 价格异常自动推送，Header 铃铛 + 抽屉 + 全页
- **全局搜索**：一个输入框跨 PR / PO / 合同 / 发票 / 供应商 / 物料搜索（pg_trgm + tsvector）
- **系统参数可配置**：14 个硬编码阈值（审批金额 / JWT 有效期 / SKU 窗口 / 合同提醒 / 上传限制 …）全部从 Admin 控制台编辑
- **多级审批 DSL**：按 `biz_type + 金额区间` 路由多阶段串签，支持**审批代理人**（出差临时委托）
- **主数据 CRUD**：供应商 / 物料 / 公司 / 部门 的增删改查 + 部门树层级 + 审计日志
- **PDF / Excel 导出**：PO 导出 PDF（供应商签章版）· 付款记录导出 Excel（财务交接）
- **运维脚本**：一键备份 / 恢复 / 升级（自动回滚）/ 健康检查 / 日志聚合
- **打印样式**：审批单 / PO 详情 / 合同页 `@media print` 自动隐藏应用外壳

### 规划中
- 飞书集成（消息通知 + 审批卡片联动） — v0.6
- 单元测试覆盖率 + CI — v0.6
- 真实 LLM 集成演示（通义 / 豆包 / DeepSeek / OpenAI 之一） — v0.6
- Cerbos sidecar 化（目前策略内嵌于代码） — v0.6+
- ADFS SAML SSO 真实对接 — 待企业 IdP 测试环境就绪

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + Zustand |
| 设计系统 | 自研 tokens（水獭棕 + 冷暖灰）+ AntD 双主题 + Inter 字体 |
| 国际化 | react-i18next（前端）+ 自研消息字典（后端） |
| 数据库 | PostgreSQL 16 + pg_trgm（中文全文检索，轻量方案） |
| 全文检索 | pg_trgm + tsvector（zhparser 保留为 v0.7+ 升级路径） |
| LLM 网关 | LiteLLM SDK（支持 OpenAI / DeepSeek / 通义 / 豆包 等 ~100 家） |
| OCR | pdfplumber + pymupdf + easyofd + LLM Vision 兜底 |
| 导出 | reportlab（PDF，含 STSong-Light 中文字体） + openpyxl（Excel） |
| 权限引擎 | 字段级 authz（`core/field_authz.py`）+ Cerbos 规划中 |
| 部署 | Docker Compose v2 + Nginx |

## 仓库结构

```
mica/
├── backend/              # FastAPI 后端服务
│   ├── app/
│   │   ├── api/v1/       # REST 端点（notifications / search / approval_rules / approval_delegations / …）
│   │   ├── services/     # 业务服务层（system_params / notifications / search / master_data / export_pdf / export_excel / …）
│   │   ├── models/       # SQLAlchemy 2 模型（单文件 ~895 行）
│   │   ├── schemas/      # Pydantic v2 schemas
│   │   ├── core/         # 安全 / authz / 国际化
│   │   └── i18n/         # zh-CN / en-US 消息字典
│   └── migrations/       # Alembic 迁移（v0.5 含 6 个）
├── frontend/             # React 前端
│   ├── src/
│   │   ├── theme/        # 设计 tokens + AntD theme + ThemeProvider
│   │   ├── components/   # UI 原语 + GlobalSearch / NotificationBell / PrintButton / …
│   │   ├── pages/        # Dashboard / SearchResults / NotificationCenter / Admin / 业务主线
│   │   ├── stores/       # Zustand stores（notification / …）
│   │   ├── api/          # 按模块的 API 包装
│   │   ├── styles/       # global.css（tokens + print + 响应式）
│   │   ├── i18n/         # 前端 i18n
│   │   └── assets/       # 水獭 SVG 插画
├── deploy/
│   ├── docker-compose.yml
│   ├── nginx/
│   ├── postgres/
│   └── scripts/          # dev-up / dev-down / backup / restore / upgrade / health / logs
├── docs/                 # 公开文档（ADR / 用户手册 / Quickstart / Development）
├── scripts/              # 开发/运维辅助
└── .github/              # CI/CD 与 Issue 模板
```

## 快速开始

```bash
cd deploy
./scripts/dev-up.sh
```

约 90 秒后访问 <http://localhost:8900>（本机）或 `http://<LAN-IP>:8900`（同网段其它设备）。

**默认种子账号**（所有密码均为 `MicaDev2026!`）：
- `admin` — 管理员（看全貌）
- `alice` — IT 采购员（提单主力）
- `bob` — 部门负责人（审批）
- `carol` — 财务审核（付款）
- `dave` — 采购经理（大额审批）

详见 [docs/QUICKSTART.md](docs/QUICKSTART.md) 与 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 运维脚本（v0.5 新）

```bash
cd deploy

./scripts/health.sh              # 健康检查（人读表格或 --json）
./scripts/backup.sh              # 备份 DB + media volume
./scripts/restore.sh <archive>   # 从归档恢复（双重确认）
./scripts/upgrade.sh             # 升级：备份 → 构建 → 迁移 → 健康检查（失败自动回滚）
./scripts/logs.sh backend        # 查看容器日志
```

详见 [deploy/scripts/README.md](deploy/scripts/README.md)。

## 文档

- [用户手册](https://helixzz.github.io/mica/)
- [Quickstart（3 分钟）](docs/QUICKSTART.md)
- [开发指南](docs/DEVELOPMENT.md)
- [架构决策记录 (ADR)](docs/adr/)

## 版本路线

| 里程碑 | 状态 | 主题 |
|---|---|---|
| v0.1 - v0.3 | ✅ | 基础设施 · 权限 · 审批 · 采购主线 |
| v0.4 | ✅ | LLM 接入 · 分批能力 · 管理员控制台 |
| v0.4.2 | ✅ | SKU 行情库 · 合同 OCR · 发票详情 |
| **v0.5.0** | ✅ | **UI 品牌化 · 通知中心 · 全局搜索 · 系统参数 · 多级审批 · 主数据 CRUD · PDF/Excel 导出 · 运维脚手架** |
| **v0.6.0** | ✅ | **单元测试 103 个 · CI 覆盖率 · 代码分割 (-97%) · Dashboard 趋势 · 暗色模式 QA · 水獭插画升级 · Cerbos 授权 · LLM 真实接入** |
| v0.7 | 🚧 | 飞书集成 · 覆盖率硬阈值 · 批量导入 Excel |
| v0.7+ | 📋 | Cerbos 独立 · 批量导入 · 多级审批可视化编辑器 · zhparser 升级 |

## 许可

本项目采用 **Apache License 2.0** 授权。详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

## 致谢

- 水獭插画与吉祥物设计 — 内部原创
- 字体 — [Inter](https://rsms.me/inter/)（OFL）
- PDF 中文字体 — Adobe STSong-Light CID（reportlab 捆绑）
