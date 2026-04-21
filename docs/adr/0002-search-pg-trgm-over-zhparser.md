# ADR 0002 — 全文检索：pg_trgm 而非 zhparser（v0.5）

## 状态

已采纳 · 2026-04-21 · v0.5.0 交付

## 背景

v0.5 规划在后端引入"统一全文搜索"端点，一次查询跨 7 张业务表（PR / PO / 合同 / 合同文档 / 发票 / 供应商 / 物料）。中文分词是核心需求。

ADR 0001 最初方向是 **PostgreSQL zhparser**（SCWS 算法，中文词边界识别精度高）。在 v0.5 实施阶段，选型被重新评估。

## 决策

选用 **`pg_trgm` 扩展 + `tsvector` 简易分词（`simple` 配置）** 的组合，放弃 zhparser。

- `pg_trgm` 提供三元组（trigram）相似度匹配 + GIN 索引，适合中文子串查询
- `tsvector`（配合 `simple` 分词器而非 `chinese`）提供 `ts_rank` 排名 + `ts_headline` 摘要高亮
- 两者组合覆盖 "包含型" + "排名型" 查询，精度足以满足企业内部 < 1000 条业务记录规模

## 理由

### 1. 部署简洁性（最关键因素）

zhparser 不包含在 `postgres:16-alpine` 官方镜像中，需自己编译 C 扩展或切换到社区定制镜像（如 `imbolc/pg-zhparser`）。这会破坏 Mica 的核心体验：

> `docker compose up -d` 后 3 分钟内一键启动端到端业务

切换到非官方镜像引入信任链 + 漏洞追踪成本；自编译 PG 镜像维护成本过高（每次 PG 小版本升级都要重编）。

`pg_trgm` 是 PostgreSQL 官方 contrib 扩展，`postgres:16-alpine` 已自带，一条 `CREATE EXTENSION IF NOT EXISTS pg_trgm` 即启用。

### 2. 精度差距在实际业务场景下可接受

Mica 的搜索场景是 **"找采购单 / 找合同 / 找供应商"**，用户输入通常是：

- 订单号（`PR-2026-0001`）— 精确匹配，两种方案都完美
- 供应商名（"戴尔"、"华为"）— 短词子串，pg_trgm 足够
- 物料名（"MacBook"、"服务器"）— 混合中英文，pg_trgm 的字符 n-gram 策略天然处理
- 合同 OCR 全文 — 长文本查询，zhparser 优势在此显现，但企业场景下用户很少输入长句查询

trigram 的不足主要在 **搜索"公司"时会匹配到"公司法人"** 等边界模糊场景，但对企业内部系统而言，用户通常愿意多输入几个字符或使用列表页筛选辅助。

### 3. 未来可升级路径清晰

`tsvector` 列和 GIN 索引已就位，从 `simple` 切到 `chinese`（zhparser）只需 `ALTER TEXT SEARCH CONFIGURATION` + `REINDEX`，不需改应用代码。当业务规模或精度需求上升到某个阈值时（估算：合同 > 5000 份 / 用户投诉搜不到某中文关键词），升级路径只涉及 PG 镜像 + 一个 Alembic migration。

## 后果

### 正面

- `docker compose up` 零配置可用
- 官方支持 + 稳定性可预期
- 7 张表的 `search_vector` 生成列 + GIN 索引已交付（migration `0004_fts_trigram`）
- 统一搜索端点 `GET /api/v1/search?q=&types=&limit=` 已接通前端

### 负面

- 对长中文文本（合同 OCR）精度不如 zhparser，尤其在 **多字复合词边界**（如"总经理办公室" vs "总 / 经理 / 办公室"）
- `ts_headline` 在 simple 配置下的摘要不如专业中文分词器自然

### 需关注

- 如果合同模块迭代到 **"智能语义搜索"**（如"找去年和 xx 公司签的所有合同"），那时可能需要升级到 zhparser + embedding 混合检索
- 记入 v0.7+ roadmap

## 参考

- `backend/migrations/versions/0004_fts_trigram.py` — 实施细节
- `backend/app/services/search.py` — 服务层
- `backend/app/api/v1/search.py` — REST 端点
- PostgreSQL pg_trgm: <https://www.postgresql.org/docs/current/pgtrgm.html>
- zhparser: <https://github.com/amutu/zhparser>（作为升级路径保留）
