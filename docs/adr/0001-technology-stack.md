# ADR 0001 — 技术栈锁定（Walking Skeleton v0.0.1）

- **状态**：Accepted
- **日期**：2026-04-21

## 背景

Mica 进入实施阶段。为避免后期大幅重构，在首版 Walking Skeleton 确立完整技术栈。该技术栈需在小规模 (<100 用户) 下简单部署、在活跃迭代中易于升级、为未来的企业能力 (SSO / 权限引擎 / LLM / 审批引擎 / 分批业务模型) 预留扩展点。

## 决策

### 后端
- **语言**：Python 3.12
- **框架**：FastAPI（异步、原生类型、OpenAPI、SSE 友好）
- **ORM**：SQLAlchemy 2.x (async) + Alembic 迁移
- **数据库**：PostgreSQL 16（JSONB / tsvector / RLS 一站式）
- **校验**：Pydantic 2 + pydantic-settings
- **安全**：passlib[bcrypt] + python-jose (JWT)

### 前端
- **构建**：Vite
- **框架**：React 18 + TypeScript
- **UI 库**：Ant Design 5（面向内部管理系统的成熟组件库）
- **路由**：React Router v6
- **状态管理**：Zustand（轻量）
- **i18n**：react-i18next + browser-languagedetector
- **HTTP**：axios

### 部署与运维
- **编排**：Docker Compose v2
- **Web 反代**：Nginx
- **升级策略**：Alembic migrate init 容器 + 可回滚策略（M1 之后引入）
- **CI/CD**：GitHub Actions

### 未来模块（Walking Skeleton 阶段**不引入**，但已预留）
- **权限引擎**：Cerbos sidecar（v0.3 引入）
- **审批引擎**：自研轻量引擎（v0.3 引入）
- **LLM 网关**：LiteLLM SDK（v0.4 引入）
- **OCR**：RapidOCR (快速) + LLM Vision (智能)，双通道架构（v0.6 引入）
- **身份认证**：ADFS SAML via python3-saml（v0.2 引入，Walking Skeleton 用本地密码账号）
- **文档生成**：xltpl (Excel) + WeasyPrint + pypdf (PDF)（v0.4+ 引入）
- **对象存储**：MinIO（v0.6 引入）
- **缓存 / 异步**：Redis（按需引入）
- **飞书集成**：自建应用 + 3 权限码（v0.7 引入）

## 实施说明（v0.5.0, 2026-04-21）

v0.0 - v0.5 迭代过程中，部分选型根据实施可行性作出调整，记录如下：

- **OCR 方案**：未采用 RapidOCR（需 ONNX runtime + 模型权重，镜像膨胀）。v0.4.2 改用 `pdfplumber + pymupdf + easyofd + LLM Vision 兜底` 的 4 级分层策略，更轻量。
- **文档生成**：未采用 `xltpl + WeasyPrint`。v0.5 改用 `reportlab`（PDF，纯 Python；含 STSong-Light CID 中文字体）+ `openpyxl`（Excel）。WeasyPrint 需要 pango/cairo 系统库，reportlab 方案更易容器化。
- **全文检索**：最初倾向 `zhparser`，v0.5 改为 `pg_trgm + tsvector` 轻量组合。`postgres:16-alpine` 官方镜像不含 zhparser，引入自定义镜像会破坏 `docker compose up` 一键启动体验。详见 [ADR 0002](./0002-search-pg-trgm-over-zhparser.md)。
- **Cerbos**：v0.5 仍未引入独立 sidecar，字段级权限内嵌于 `core/field_authz.py`。Cerbos 化规划至 v0.6+。
- **ADFS SAML**：骨架已就绪，实际对接等企业 IdP 测试环境。
- **对象存储**：v0.5 仍使用本地 `media/` volume，MinIO 引入推迟至集群部署阶段。
- **新增依赖**：v0.5 引入 `reportlab`、`openpyxl`、`@fontsource/inter`、`zustand`、`python-jose`。

## 依据

本决策基于 9 份并行技术调研的综合结论，涉及 ADFS SAML、飞书最小权限、OCR 全文检索、Excel/PDF 生成、LLM 企业集成、轻量审批工作流、内网部署运维、字段级/行级权限、采购分批模型。完整调研记录与对比矩阵保留于项目内部档案库。

## 影响

- Walking Skeleton 能在 `docker compose up -d` 后 3 分钟内启动并验收端到端业务流程
- 每个未来模块引入时**无需改动骨架架构**：新依赖通过 `pyproject.toml` 增补、新服务通过 Docker Compose 扩展、新前端包通过 `package.json` 增补
- Alembic 的迁移系统从第一天就就位，保证 v0.0.1 → v1.0 的数据库演进零断层
- i18n 基础设施 (react-i18next + FastAPI 消息字典) 从第一天就就位，避免后期对散落字符串的批量改造

## 参考

- FastAPI: <https://fastapi.tiangolo.com/>
- SQLAlchemy 2.0 async: <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>
- Ant Design: <https://ant.design/>
- react-i18next: <https://react.i18next.com/>
