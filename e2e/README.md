# 端到端测试

改动前端交互后，用这套流程验收，不要靠人点。

## 一键运行

```bash
./e2e/run-local.sh                              # 全部
./e2e/run-local.sh tests/rfq-collection.spec.ts # 单个文件
```

脚本会：迁移数据库 → 灌种子数据 → 起后端与前端 → 跑 Playwright → 退出时停掉服务。

前置条件：可连的 PostgreSQL、`backend/.venv`、`e2e/` 已 `npm install`。
默认连 `postgresql+asyncpg://mica:mica@localhost:5432/mica_e2e`，可用
`E2E_DATABASE_URL` / `E2E_PSQL_URL` 覆盖。

## 为什么要灌种子

CI 的 smoke 库里只有账号和供应商，凡是要业务对象（订单、已发出的询价单）的
spec 都会 skip——于是"测试通过"不等于"功能可用"，最后仍靠人工验收。
`seed_data.py` 补上这些对象，spec 就能真的跑。

种子内容：一张已确认的采购订单、一张已发出且逾期的询价单（用于验证待取回与逾期标红）。

## 新增 spec 的约定

- 缺数据时用 `test.skip(...)` 而不是硬失败，别让 smoke 环境红
- 登录统一走 `helpers/auth.ts`
- 仪表盘有欢迎态：spec 里要 `localStorage.setItem('mica.welcome_dismissed', '1')`，
  否则所有卡片都被欢迎卡挡住

## 为什么串行

所有 spec 共用同几个测试账号，并行 worker 同时登录会触发限流，表现为
`waitForURL` 超时之类的**假失败**——单独跑那个文件又通过了。`playwright.config.ts`
里固定 `workers: 1`。全量 56 项约 2 分钟，比查假失败便宜。
