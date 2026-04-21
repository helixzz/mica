# 开发者指南

## 本地开发（非 Docker 方式）

### 后端

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 启动 Postgres（用 Docker 最方便）
docker run -d --name mica-pg -p 5432:5432 \
  -e POSTGRES_USER=mica -e POSTGRES_PASSWORD=mica -e POSTGRES_DB=mica \
  postgres:16-alpine

# 运行迁移
alembic upgrade head

# 启动 API
uvicorn app.main:app --reload
```

- API 文档：<http://localhost:8000/api/docs>
- 首次启动会自动种子化 demo 数据（由 `app.services.seed.seed_dev_data` 驱动）

### 前端

```bash
cd frontend
npm install
npm run dev
```

- 前端开发服务器：<http://localhost:5173>
- 请求通过 Vite proxy 转到 <http://localhost:8000/api>
- 默认代理目标可通过 `VITE_API_TARGET` 覆盖

## 项目目录约定

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # pydantic-settings
│   ├── db/                # SQLAlchemy engine + session
│   ├── models/            # ORM
│   ├── schemas/           # Pydantic request/response
│   ├── core/              # security, deps
│   ├── i18n/              # 后端消息字典 + messages/*.json
│   ├── api/v1/            # FastAPI routers
│   └── services/          # 业务逻辑
├── migrations/            # Alembic
└── tests/
frontend/
├── src/
│   ├── api/               # axios + DTO + API 函数
│   ├── auth/              # 登录态
│   ├── i18n/              # react-i18next + locales/
│   ├── components/        # Layout, LanguageSwitcher, GlobalSearch, NotificationBell, ui/*
│   ├── pages/             # 每个业务视图一个目录
│   ├── stores/            # Zustand（notification 等）
│   ├── theme/             # tokens.ts / antdTheme.ts / ThemeProvider.tsx
│   ├── styles/            # global.css（CSS vars + print + 响应式）
│   ├── assets/            # illustrations/otter-*.svg 等
│   └── routes/
deploy/
├── docker-compose.yml
├── .env.example
├── nginx/conf.d/mica.conf
└── scripts/               # dev-up / dev-down / backup / restore / upgrade / health / logs
```

## 数据库迁移

```bash
cd backend
# 生成新迁移
alembic revision --autogenerate -m "add foo table"

# 应用
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

生产部署：`migrate` 容器在每次 `docker compose up` 时自动运行 `alembic upgrade head`，backend 等待其完成后才启动。

## 添加新语言 / 新翻译 Key

### 后端
- 编辑 `backend/app/i18n/messages/zh-CN.json` 和 `en-US.json`
- 代码中：`from app.i18n import t; raise HTTPException(400, detail=t("pr.no_items", locale))`

### 前端
- 编辑 `frontend/src/i18n/locales/{zh-CN,en-US}/common.json`
- 组件中：`const { t } = useTranslation(); t("button.submit")`
- 新模块建议新建 namespace，例如 `purchase.json`，在 `frontend/src/i18n/index.ts` 注册

## 代码质量

```bash
# 后端
cd backend
ruff check app
ruff format app
mypy app

# 前端
cd frontend
npm run type-check
```

## 测试

### 后端
```bash
cd backend
# 需要 Postgres test DB
createdb mica_test   # 或 docker exec mica-postgres createdb -U mica mica_test
pytest -m integration
```

## 添加 API 路由

1. 在 `backend/app/api/v1/` 新建 `my_module.py`
2. 在 `backend/app/api/__init__.py` `api_router.include_router(...)`
3. 业务逻辑放 `backend/app/services/`
4. 数据模型放 `backend/app/models/`（现在单一 `__init__.py`，未来按领域拆分）
5. 前端 `src/api/index.ts` 增加对应调用

## 添加系统参数（v0.5+）

当需要新增一个 **可配置阈值** 时，不要直接硬编码常量：

1. 在 `backend/migrations/versions/` 新增迁移，通过 `op.bulk_insert` 加一行到 `system_parameters`：
   ```python
   {
     "key": "myfeature.max_items",
     "category": "myfeature",
     "value": 100,
     "default_value": 100,
     "data_type": "int",
     "min_value": 1,
     "max_value": 1000,
     "unit": "count",
     "description_zh": "X 功能的最大条数",
     "description_en": "Maximum items for X feature",
   }
   ```
2. 在对应服务里读取：`from app.services.system_params import system_params; limit = await system_params.get_int(db, "myfeature.max_items")`
3. 前端 Admin 控制台的 "系统参数" Tab **自动显示**（无需改代码），按 category 折叠

参见 [ADR 0003](./adr/0003-system-parameters.md)。

## 添加审批规则（v0.5+）

多级串签通过 `approval_rules` 表配置：

```python
{
  "name": "付款审批（大额）",
  "biz_type": "payment",
  "amount_min": 500000,
  "amount_max": None,
  "stages": [
    {"stage_name": "财务审核", "approver_role": "finance_auditor", "order": 1},
    {"stage_name": "CFO 审批", "approver_role": "procurement_mgr", "order": 2},
  ],
  "is_active": True,
  "priority": 10,
}
```

创建方式：通过 Admin 控制台 / `POST /api/v1/approval-rules` 或 Alembic seed 迁移。`services/approval.py` 在处理 PR 提交时会按 `biz_type + is_active + 金额区间 + priority 升序` 选中第一条匹配规则。

## 添加通知类型（v0.5+）

新增一种通知场景：

1. 在 `NotificationCategory` enum 添加新值（`backend/app/models/__init__.py`）
2. 在业务服务的合适位置调用 `create_notification(db, user_id=..., category=NotificationCategory.X, title=..., link_url=..., biz_type=..., biz_id=..., meta={...})`
3. 在 i18n 添加 `notification.x.xxx` 翻译 key（zh-CN + en-US）
4. 前端 `components/NotificationBell/NotificationBell.tsx` 的 category → 图标/颜色 map 加一条

## 运维脚本（v0.5+）

`deploy/scripts/` 下有 5 个 pure bash 脚本：

- `health.sh` — 健康检查（人读 + `--json`）
- `backup.sh` — 备份 DB + media volume
- `restore.sh` — 从备份恢复
- `upgrade.sh` — 一键升级（自动备份 + 失败回滚）
- `logs.sh` — 容器日志聚合

脚本设计原则：纯 bash + `docker compose` + `curl`，无 Python/Node 依赖。详见 `deploy/scripts/README.md`。

## 里程碑

见 [CHANGELOG.md](../CHANGELOG.md) 与 [README.md](../README.md) 的"版本路线"章节。
