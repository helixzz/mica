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
│   ├── components/        # Layout, LanguageSwitcher
│   ├── pages/             # 每个业务视图一个目录
│   └── routes/
deploy/
├── docker-compose.yml
├── .env.example
├── nginx/conf.d/mica.conf
└── scripts/               # dev-up.sh / dev-down.sh / ...（未来加 upgrade / backup）
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

## 里程碑

见 `../README.md` 或内部档案 `mica-internal/progress/current-milestone.md`。
