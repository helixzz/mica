# Mica｜觅采

企业内部采购管理系统 — 服务 IT 部门为主，渐进扩展至其他部门。

- **中文名**：觅采
- **英文名**：Mica
- **定位**：企业内部采购管理系统（Internal Procurement Management System）
- **状态**：🚧 设计阶段（M0）

---

## 设计理念

> **效率优先 > 扩展性 > 标准化管控**
> 系统服务于人，而不是限制人。

Mica 面向的是一个 < 100 人规模、月均 < 300 单的企业场景，采用深度定制而非通用 SaaS，以便与团队既有工作流完美契合。

## 核心特性（规划中）

- 多公司主体（法人）+ 多币种预留
- **多语言支持**：中文简体 / 英文，浏览器自动检测 + 用户手动切换
- 采购申请 → 审批 → 合同 → 多批次交货 → 分批付款 → 发票三单匹配
- 字段级 + 行级细粒度权限
- **LLM 一等公民能力**：表单智能填写、信息抽取、价格异常预警、智能 OCR
- SKU 行情库与价格异常检测
- 飞书集成（消息通知 + 付款审批联动）
- ADFS SAML SSO
- 文档中心（合同归档 + OCR 全文检索）

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic |
| 前端 | React + TypeScript + Vite + Ant Design |
| 多语言 | react-i18next（前端）+ 自研消息字典（后端） |
| 数据库 | PostgreSQL 16 + zhparser（中文全文检索） |
| 缓存/队列 | Redis 7 |
| 对象存储 | MinIO |
| 权限引擎 | Cerbos + PostgreSQL RLS 兜底 |
| LLM 网关 | LiteLLM SDK |
| OCR | RapidOCR（快速通道）+ LLM Vision（智能通道） |
| 部署 | Docker Compose v2 + Nginx |

## 仓库结构

```
mica/
├── backend/              # FastAPI 后端服务
├── frontend/             # React 前端应用
├── deploy/               # 部署脚本、Docker Compose、Nginx、Cerbos 策略
├── docs/                 # 公开文档（ADR、API、用户手册）
├── scripts/              # 开发/运维辅助脚本
└── .github/              # CI/CD 与 Issue 模板
```

## 文档

- [架构决策记录 (ADR)](docs/adr/)
- [API 参考](docs/api/)
- [用户手册](docs/user-manual/)

## 开发与部署

```bash
cd deploy
./scripts/dev-up.sh
```

约 90 秒后浏览器访问 <http://localhost>。详见 [docs/QUICKSTART.md](docs/QUICKSTART.md) 与 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 许可

本项目采用 **Apache License 2.0** 授权。详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

选择 Apache 2.0 的原因：
- 包含**专利授权**条款，企业使用更放心
- 要求**修改声明**与**版权保留**，比 MIT 更适合企业项目
- 广泛被主流开源基础设施采用（Kubernetes、Apache 基金会项目等），兼容性好

## 项目状态

| 里程碑 | 阶段 | 时长 |
|---|---|---|
| M0 | 设计定稿 | 2 周 |
| M1 | 基础设施 | 3 周 |
| M2 | 权限 + 审批引擎 | 3 周 |
| M3 | 采购主线 MVP | 4 周 |
| M4 | 分批能力 | 3 周 |
| M5 | 飞书集成 + 文档 | 2 周 |
| M6 | LLM 能力 | 3 周 |
| M7 | SKU 行情库 | 2 周 |
| M8 | 运维打磨 | 2 周 |
