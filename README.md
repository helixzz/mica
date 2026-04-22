# Mica｜觅采

企业内部采购管理系统 — 服务 IT 部门为主，渐进扩展至其他部门。

- **中文名**：觅采
- **英文名**：Mica
- **定位**：企业内部采购管理系统（Internal Procurement Management System）
- **状态**：✅ v0.7.3 — i18n 全量覆盖 + 权限优化 + Bug 修复（2026-04-22）

---

## 设计理念

> **效率优先 > 扩展性 > 标准化管控**
> 系统服务于人，而不是限制人。

## 已交付能力

### 采购主线（v0.1 - v0.4）
- 多公司主体 + 多币种
- 中文 / 英文双语（浏览器自动检测 + 用户手动切换）
- 采购申请 → 审批 → 订单 → 多批次交货 → 分批付款 → 发票三单匹配
- 字段级 + 行级细粒度权限（多级串签 + 审批代理人）
- 合同全生命周期（归档 + OCR 全文检索 + 到期提醒 + **付款计划**）
- SKU 行情库（90 天基准价 + ±20% 异常识别 + **多选对比折线图**）
- 发票 AI 抽取（PDF/OFD/图片 → LLM 结构化 → 人工复核）

### v0.5 — UI 品牌化 + 运维脚手架
- 水獭棕 `#8B5E3C` 品牌色系 + 浅色 / 暗色双主题 + 响应式布局
- 通知中心（审批 / 合同到期 / 价格异常自动推送）
- 全局搜索（一个输入框跨 PR / PO / 合同 / 发票 / 供应商 / 物料）
- 系统参数可配置（15+ 个运行时阈值，Admin 控制台编辑）
- 多级审批 DSL（按 `biz_type + 金额区间` 路由多阶段串签 + 代理人委托）
- 主数据 CRUD + PDF / Excel 导出 + 运维脚本（备份 / 恢复 / 升级 / 健康检查）

### v0.6 — 测试 + 质量 + 新功能
- **自动化测试 114 个**：backend pytest 82 + frontend vitest 32；CI 覆盖率上传 Codecov
- **代码分割**：main JS chunk 1.5 MB → 42 KB (-97%)；16 页面 React.lazy 按需加载
- **Dashboard 月环比趋势**：4 个 StatCard 显示 ↑/↓/— 百分比变化
- **暗色模式 QA**：Playwright 截图验收 + tokens 对比度提亮
- **水獭 SVG v2**：3 张详细矢量插画替代几何占位
- **Cerbos 授权**：sidecar 策略引擎 + 4 个 resource policy + graceful fallback
- **LLM 真实接入**：OpenAI 兼容路由修复 + Embedding 支持 + reasoning 模型 max_tokens 适配
- **合同付款计划**（v0.6.1）：按期管理付款（4 种触发条件）+ 财务预测 + 执行自动创建 PaymentRecord
- **SKU 多选折线图**（v0.6.1）：交互式 SVG 价格走势对比（10 色调色板 + tooltip）
- **采购分类体系**（v0.6.2）：成本中心 / 开支类型 / 采购种类（2 级层级）+ Admin CRUD + PR 表单下拉框

### 规划中
- 飞书集成（消息通知 + 审批卡片联动） — v0.7
- 覆盖率硬阈值 + 批量导入 Excel — v0.7
- ADFS SAML SSO 真实对接 — 待企业 IdP 测试环境就绪

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + Zustand |
| 设计系统 | 自研 tokens（水獭棕 + 冷暖灰）+ AntD 双主题 + Inter 字体 |
| 国际化 | react-i18next（前端）+ 自研消息字典（后端） |
| 数据库 | PostgreSQL 16 + pg_trgm（中文全文检索） |
| 授权引擎 | Cerbos sidecar（4 resource policies + graceful fallback） |
| LLM 网关 | LiteLLM SDK（支持 OpenAI / DeepSeek / 通义 / 豆包 / GLM 等） |
| 测试 | pytest + pytest-asyncio（82 tests）/ vitest + testing-library（32 tests） |
| CI/CD | GitHub Actions（lint + test + coverage + docker build）+ Codecov |
| 部署 | Docker Compose v2 + Nginx + Cerbos sidecar |

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

## 运维脚本

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
| v0.5.0 | ✅ | UI 品牌化 · 通知中心 · 全局搜索 · 系统参数 · 多级审批 · PDF/Excel 导出 · 运维脚手架 |
| v0.6.0 | ✅ | 单元测试 103 个 · CI 覆盖率 · 代码分割 · Dashboard 趋势 · 暗色模式 QA · Cerbos 授权 · LLM 真实接入 |
| **v0.6.1** | ✅ | **合同付款计划 · SKU 多选价格走势图** |
| **v0.6.2** | ✅ | **采购分类体系（成本中心 / 开支类型 / 采购种类 2 级层级）** |
| **v0.7.0-v0.7.2** | ✅ | **RFQ 询价 · Excel 导入 · 角色化 Dashboard · 列表筛选 · 物料管理 · 审批规则编辑** |
| **v0.7.3** | ✅ | **i18n 全量覆盖（424→0 硬编码）· 权限优化 · 物料分类 Bug 修复** |
| v0.8 | 🚧 | 飞书集成 · 覆盖率硬阈值 · E2E 浏览器测试 |

## 许可

本项目采用 **Apache License 2.0** 授权。详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

## 致谢

- 水獭插画与吉祥物设计 — 内部原创
- 字体 — [Inter](https://rsms.me/inter/)（OFL）
- PDF 中文字体 — Adobe STSong-Light CID（reportlab 捆绑）
