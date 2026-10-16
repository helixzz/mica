# Mica API 接入指南（Personal Access Token）

面向 **外部系统 / 运维脚本 / AI Agent** 的接入文档。Mica 的 REST API 用 **Personal Access Token（PAT）** 做机器身份认证：一个长期有效、可撤销、可审计的凭据，权限等于签发它的那个人的角色权限。

- 交互式参考（全部端点、请求/响应 schema）：`/api/docs`（Swagger UI）
- 机器可读契约：`/api/openapi.json` · 人类可读：`/api/redoc`
- 设计依据：[ADR 0004 — 对外 API 认证：Personal Access Token](./adr/0004-api-personal-access-tokens.md)

> 本文中的 base URL 统一写作 `$MICA_BASE`（例如 `https://mica.example.internal`）。API 前缀是 `/api`，业务端点挂在 `/api/v1/...` 下。

---

## 一分钟上手

### 1. 创建令牌

登录 Mica → 左侧导航 **API 令牌**（`/settings/api-tokens`）→ **新建令牌**。

| 字段 | 说明 |
|---|---|
| 名称 | 必填，1–64 字符。给自己看的用途标签，例如 `ci-inspect-script` |
| 权限范围 | `read`（只读）或 `write`（读写）。只做查询就选 `read` |
| 有效期 | 天数。省略时取系统参数 `api.token.default_ttl_days`（默认 90 天），超过 `api.token.max_ttl_days`（默认 365 天）会被拒绝 |

**明文令牌只在创建（或轮换）的那一次响应里返回，之后任何接口都不会再显示。** 立刻存进密钥管理器（Vault / CI secret / 系统环境变量），不要贴进聊天、issue、代码或提示词。

### 2. 发起第一条请求

```bash
export MICA_BASE="https://mica.example.internal"
export MICA_PAT="mica_pat_xxxxxxxx_yyyyyyyyyyyyyyyyyyyyyyyy"

# 列出你可见的采购申请（PR）
curl -sS "$MICA_BASE/api/v1/purchase-requisitions" \
  -H "Authorization: Bearer $MICA_PAT" \
  | jq '.[0:3]'

# 查询单个 PR
curl -sS "$MICA_BASE/api/v1/purchase-requisitions/$PR_ID" \
  -H "Authorization: Bearer $MICA_PAT" \
  | jq '{pr_number, status, total_amount}'
```

PR 列表接口没有分页参数，返回的是**该用户可见范围**内的全部 PR（行级过滤照常生效），因此上面用 `jq '.[0:3]'` 只截取前三条。

### 3. 确认令牌有效

```bash
# 这是唯一允许 PAT 访问的 /auth 端点
curl -sS "$MICA_BASE/api/v1/auth/me" -H "Authorization: Bearer $MICA_PAT" | jq
```

---

## 认证

### 两种凭据，同一个入口

Mica 的所有 REST 端点走**同一个认证依赖** `get_current_user`（`backend/app/core/security.py`）。它按 `Authorization` 头的值自动分流：

| 凭据 | 形态 | 来源 | 典型用途 |
|---|---|---|---|
| JWT | `Authorization: Bearer eyJhbGciOi...` | 人类在 UI 登录后签发，短时效 | 浏览器内的前端 |
| **PAT** | `Authorization: Bearer mica_pat_<prefix>_<secret>` | 左侧导航「API 令牌」页面签发，长期有效、可撤销 | 脚本、外部系统、AI Agent |

请求头格式固定：

```http
Authorization: Bearer mica_pat_<prefix>_<secret>
```

### 令牌形态与存储

```
mica_pat_<prefix>_<secret>
│         │         └── 高熵随机 secret：真正的凭据，只在创建/轮换时返回一次
│         └── 明文 prefix：可安全展示，用于列表显示与索引查找
└── 固定前缀，便于密钥扫描工具识别
```

服务端只保存 `sha256(secret)`，另有明文 `prefix` 用于展示与索引查找。校验时先按 `prefix` 定位候选行，再做常量时间的 hash 比对。**数据库里没有可以直接使用的明文令牌**，泄漏一份数据库备份不等于泄漏可用凭据（前提是 secret 随机性足够）。

### 禁止在 URL query 里传令牌

```bash
# ❌ 不要这样：令牌会进 Nginx access log、浏览器历史、Referer、错误上报
curl "$MICA_BASE/api/v1/me/tokens?token=$MICA_PAT"
```

只接受 `Authorization: Bearer` 请求头。query 传参一律不被识别，且已明确列为不支持的用法。

---

## 令牌生命周期

| 动作 | 端点 | 语义 |
|---|---|---|
| 创建 | `POST /api/v1/me/tokens` | 返回一次明文 `token`；总数受 `api.token.max_per_user` 限制 |
| 列表 | `GET /api/v1/me/tokens` | 只返回元数据，**永不返回明文或 hash** |
| 轮换 | `POST /api/v1/me/tokens/{id}/rotate` | 签发新 secret，**旧令牌立即失效** |
| 撤销 | `DELETE /api/v1/me/tokens/{id}` | 立刻失效；行保留（`revoked_at` 有值）供审计 |

### 创建

```bash
curl -sS -X POST "$MICA_BASE/api/v1/me/tokens" \
  -H "Authorization: Bearer $MICA_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "ci-inspect-script", "scopes": ["read"], "expires_in_days": 90}'
```

```json
{
  "id": "0f6b1c2e-8a44-4b1f-9c3d-2a7e5b6c1d90",
  "name": "ci-inspect-script",
  "prefix": "a1b2c3d4",
  "scopes": ["read"],
  "expires_at": "2027-01-14T00:00:00Z",
  "created_at": "2026-10-16T07:30:00Z",
  "token": "mica_pat_a1b2c3d4_<secret>"
}
```

- `scopes` 省略时默认 `["read"]`（只读）；显式写 `["read"]` 只读，`["read", "write"]` 读写。取值只接受 `read` / `write`。
- `name` 为 1–64 字符（首尾空白会被去掉）。
- `expires_in_days` 省略时取 `api.token.default_ttl_days`，超过 `api.token.max_ttl_days` 会被拒绝。
- `token` 字段**只在这一个响应里出现**。列表接口的结构里没有它。
- 首次创建令牌请在 UI 上完成；用 curl 创建需要先持有一个凭据（JWT，或权限覆盖目标令牌的 PAT）。

### 轮换

```bash
curl -sS -X POST "$MICA_BASE/api/v1/me/tokens/$TOKEN_ID/rotate" \
  -H "Authorization: Bearer $MICA_PAT" \
  -H "Content-Type: application/json"
```

响应体与创建一致（含新的明文 `token`），旧 secret 在同一时刻失效。适合"疑似泄漏"或"按季度轮换"场景：**不需要先撤销再创建**，因此不会出现中间的空窗期。

### 撤销

```bash
curl -sS -X DELETE "$MICA_BASE/api/v1/me/tokens/$TOKEN_ID" \
  -H "Authorization: Bearer $MICA_JWT" -o /dev/null -w '%{http_code}\n'
# 204
```

撤销后该令牌的任何后续请求都会被认证阶段拒绝（401）。撤销不删除数据库行，`revoked_at` 会保留在列表与审计里。

### 过期

`expires_at` 到点后令牌自动失效（无需人工撤销），表现为 401。列表接口用两个服务端计算的布尔字段帮你判断状态：

- `is_expired`：`expires_at` 已过
- `is_active`：未撤销且未过期（可以继续用）

---

## 权限模型

### 以用户身份行事

PAT **绑定 `user_id`**，请求以该用户的身份执行：

- `require_roles(...)` 的角色门禁照常生效
- 行级过滤（本部门 / 本公司的可见范围）照常生效
- Cerbos 字段级读权限照常生效（令牌不会看到该用户看不到的字段）

因此令牌**永远不会比它所属的人拥有更多权限**。

### 作用域只有两档

作用域是**在此之上的额外收窄**，不是权限来源：

| Scope | 含义 |
|---|---|
| `read` | 只读。调用非只读方法（POST / PUT / PATCH / DELETE）返回 403 |
| `write` | 读写。等价于"该用户在 API 里能做的一切" |

`write` 不会凭空获得用户没有的权限，只是在用户自身权限范围内不再受只读限制。

**选择建议**：巡检、报表、导出、AI 查询用 `read`；只有确实需要写入（创建 PR、提交审批、上传附件）才用 `write`，并且给写入令牌设更短的有效期。

### 只读 POST 白名单

Mica 里有一批 POST 端点是**查询语义**——它们按 HTTP 语义选了 POST（复杂筛选体、流式响应、避免超长 query），但不写业务数据。为了让只读令牌能完成最常见的巡检与导出，下列路径前缀下的 POST 在只读令牌下依然允许：

```
/search   /exports   /insights   /ai   /dashboard
```

白名单由系统参数 **`api.read_only_post_allowlist`** 配置，管理员可在 Admin → 系统参数中调整，无需重新部署。不在白名单里的 POST 一律 403。

### 三条硬边界

以下路径前缀**任何 PAT 都不可访问**，与令牌作用域无关：

| 边界 | 覆盖 | 说明 |
|---|---|---|
| `/admin/**` | 系统参数、用户/角色管理、审计日志查询 | 管理面：权限的定义者 |
| `/saml/**` | SAML SSO 断言消费 | 身份面：身份的建立过程 |
| `/auth/**` | 登录、注册、密码、令牌签发类端点 | 凭据面：唯一例外是 `GET /api/v1/auth/me`，可用于探活与读取当前身份 |

被拒时返回 **403**，`code` 为 `api_token.path_forbidden`。

### 不可自我提权

PAT **不能创建或轮换出权限超过自身的令牌**：只读 PAT 调用 `POST /api/v1/me/tokens` 或 `POST /api/v1/me/tokens/{id}/rotate` 时不能签发 `write` 令牌，被拒时返回 **403**，`code` 为 `api_token.scope_escalation`。

理由：管理类与凭据类操作必须由人类在 UI 上完成。否则 `read` 令牌只需一次调用就能变成 `write` 令牌，作用域收窄形同虚设。

### 状态码判定

| 状态码 | `code` | 含义 | 怎么办 |
|---|---|---|---|
| 401 | `not_authenticated` | 请求完全没带 `Authorization` 头 | 补上请求头 |
| 401 | `api_token.invalid` | 令牌不存在 / 已撤销 / 已过期 / 格式非法 / hash 不匹配 | 重新签发。**不要重试**，重试不会自愈 |
| 403 | `api_token.read_only` | 只读令牌调用了非只读方法，且不在白名单内 | 改用 `write` 令牌，或改为查询语义的端点 |
| 403 | `api_token.path_forbidden` | 命中硬边界（`/admin/**`、`/saml/**`、`/auth/**`） | 无 API 绕过，改由人类在 UI 上操作 |
| 403 | `api_token.scope_escalation` | 试图创建或轮换出权限超过自身的令牌 | 改用权限足够的凭据（例如登录 JWT）操作 |
| 403 | 角色相关的其他 detail | 令牌合法，但该用户的角色 / 字段级权限不允许此操作 | 不是令牌问题，找权限归属人 |
| 400 | `api_token.invalid_name` · `api_token.invalid_scope` · `api_token.invalid_expiry` | 请求参数不合法：名称空或超过 64 字符、scope 取值非法、有效期超过 `api.token.max_ttl_days` | 修正请求体后重试 |
| 400 | `api_token.too_many` | 已达到 `api.token.max_per_user` 上限 | 撤销不再使用的令牌后再创建 |
| 404 | `api_token.not_found` | 目标令牌不存在，或不属于当前用户（非 admin 时） | 核对 `id`；admin 可在全站列表里找 |
| 429 | `api_token.rate_limited` | 超出每令牌每分钟限额 | 按 `Retry-After` 退避（见下） |

**如何区分两类 403**：`code` 为 `api_token.read_only` 是作用域问题（换 `write` 令牌可解），`api_token.scope_escalation` / `api_token.path_forbidden` 是设计上不可绕过的（换令牌无用），其余 403 是角色/字段级权限问题（换令牌也无用）。所有错误响应体统一包含：

```json
{
  "detail": "api_token.read_only",
  "code": "api_token.read_only",
  "request_id": "9f2c1e4a-..."
}
```

- `detail` / `code` 是稳定的机器可判读标识（形如 `api_token.invalid`、`api_token.read_only`、`api_token.rate_limited`、`api_token.too_many`），**请按 `code` 分支，不要匹配自然语言文本**
- `request_id` 是本次请求的追踪 ID：排障时把它连同时间戳、端点一起提供给管理员，可以在审计日志里精确定位

`api_token.too_many` 表示已达到 `api.token.max_per_user` 上限，先撤销不再使用的令牌再创建。

### 重试策略

```text
401 → 不重试，人工介入（重新签发令牌）
403 → 不重试，改权限或改端点
429 → 读 Retry-After（秒），等待后再试；指数退避 + 抖动
5xx → 可重试，指数退避 + 抖动；确认请求幂等
```

- 只对**幂等**请求自动重试（GET / PUT / DELETE）。`POST /api/v1/purchase-requisitions` 这类创建操作盲目重试会造重复单据。
- 建议：客户端侧串行化 + 单条队列，避免并发突发把配额一次打满。
- 示例（Python）：

```python
import time

def retry_after_seconds(response, default: float = 5.0) -> float:
    raw = response.headers.get("Retry-After")
    try:
        return max(1.0, float(raw)) if raw else default
    except ValueError:
        return default  # 少数代理会返回 HTTP-date，退回到默认值
```

---

## 限流与审计

### 限流

- **按令牌计**（不是按用户、IP 或端点）：每个令牌独立配额，`read` 与 `write` 令牌互不影响
- 默认 **600 次/分钟**，由系统参数 `api.rate_limit_per_minute` 控制
- 超限返回 **429** + `Retry-After` 响应头

### 审计

| 事件 | 是否写 `audit_logs` | 在哪里看 |
|---|---|---|
| 令牌创建 | ✅ 总是 | `GET /api/v1/admin/audit-logs`（admin） |
| 令牌轮换 | ✅ 总是 | 同上 |
| 令牌撤销 | ✅ 总是 | 同上 |
| 每次 API 请求 | ⚙️ 默认关闭，`api.audit_requests=true` 后写审计行 | 同上 |

请求级审计默认关闭是有意的：Mica 是内部系统，把每次读请求都落审计表会显著放大写入量。需要"完整调用链留痕"的场景（例如等保审计窗口期）再打开。

审计条目的事件类型（`audit_logs` 里可直接检索）：

| 事件类型 | 触发时机 |
|---|---|
| `api_token.created` | 创建令牌 |
| `api_token.rotated` | 轮换令牌 |
| `api_token.revoked` | 撤销令牌 |
| `api_token.request` | 单次 API 请求（仅当 `api.audit_requests=true`） |

### `last_used_at` / `last_used_ip`

这两个字段以 **60 秒节流**更新——同一个令牌在 60 秒内的多次调用只落一次时间与 IP。用途：

- **判断令牌是否还在被使用**：长期 `last_used_at` 不动的令牌可以安全撤销，减少凭据暴露面
- 排查"这个令牌到底是谁在用"

注意它的定位是**运维线索，不是取证证据**：60 秒节流意味着它不是精确的调用记录；需要精确链路时打开 `api.audit_requests`。

### 相关系统参数（category `api`）

在 **Admin → 系统参数** 中调整，全部无需重新部署：

| Key | 默认值 | 说明 |
|---|---|---|
| `api.token.max_per_user` | `10` | 每个用户可持有的令牌数上限 |
| `api.token.default_ttl_days` | `90` | 创建令牌时的默认有效期（天） |
| `api.token.max_ttl_days` | `365` | 可申请的最长有效期（天） |
| `api.rate_limit_per_minute` | `600` | 每令牌每分钟请求上限 |
| `api.audit_requests` | `false` | 是否把每次 API 请求写进审计日志 |
| `api.read_only_post_allowlist` | `/search`、`/exports`、`/insights`、`/ai`、`/dashboard` | 只读令牌下仍允许的 POST 路径前缀 |

---

## 端点速查

### 我的令牌（当前登录身份）

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/me/tokens` | 列出我的令牌，返回 `ApiToken[]` |
| `POST` | `/api/v1/me/tokens` | 创建令牌，body `{name, scopes?, expires_in_days?}` → **201**，响应含一次性 `token` |
| `POST` | `/api/v1/me/tokens/{id}/rotate` | 轮换，→ **201**，响应同创建；旧令牌立即失效 |
| `DELETE` | `/api/v1/me/tokens/{id}` | 撤销，→ **204** |

`GET /api/v1/me/tokens` 返回 `ApiToken[]`，元素字段：

```json
{
  "id": "0f6b1c2e-8a44-4b1f-9c3d-2a7e5b6c1d90",
  "name": "ci-inspect-script",
  "prefix": "a1b2c3d4",
  "scopes": ["read"],
  "expires_at": "2027-01-14T00:00:00Z",
  "revoked_at": null,
  "last_used_at": "2026-10-16T07:12:03Z",
  "last_used_ip": "192.168.1.24",
  "created_at": "2026-10-16T07:30:00Z",
  "is_expired": false,
  "is_active": true
}
```

`POST /api/v1/me/tokens` 与 `POST /api/v1/me/tokens/{id}/rotate` 的 **201** 响应字段：

```json
{
  "id": "0f6b1c2e-8a44-4b1f-9c3d-2a7e5b6c1d90",
  "name": "ci-inspect-script",
  "prefix": "a1b2c3d4",
  "scopes": ["read"],
  "expires_at": "2027-01-14T00:00:00Z",
  "created_at": "2026-10-16T07:30:00Z",
  "token": "mica_pat_a1b2c3d4_<secret>"
}
```

> 列表与创建响应的字段集**不同**：只有创建/轮换的响应带 `token`；列表响应带 `last_used_at` / `last_used_ip` / `is_expired` / `is_active` 与 `revoked_at`。

### 管理员视图（`admin` 角色）

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/admin/api-tokens?user_id=&include_revoked=&limit=&offset=` | 全站令牌列表，返回 `{items: [...], total}` |
| `DELETE` | `/api/v1/admin/api-tokens/{id}` | 强制撤销任意令牌，→ **204** |

`items` 元素在普通字段之外额外包含 `user_id`、`username`、`user_display_name`，便于按人排查。查询参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `user_id` | 不限 | 只返回该用户的令牌 |
| `include_revoked` | `false` | 设为 `true` 时连已撤销的令牌一起返回 |
| `limit` | `50` | 每页条数，范围 1–200 |
| `offset` | `0` | 偏移量 |

### 全量参考

上述 6 个端点只是令牌管理本身。**所有现有业务端点（v1 及 `/api/v2` 镜像）都自动支持 PAT**，无需逐个适配。完整端点清单、请求体 schema、响应模型请直接看：

- Swagger UI：`/api/docs` — 点 **Authorize**，在 `Value` 里填 `mica_pat_<prefix>_<secret>`（**不要**加 `Bearer ` 前缀，Swagger 会自己加），即可在页面上直接调试
- ReDoc：`/api/redoc`
- OpenAPI JSON：`/api/openapi.json`

---

## 常见接入场景

### curl

```bash
# 建议放进 ~/.netrc 或 CI secret，不要写进脚本明文
export MICA_BASE="https://mica.example.internal"
export MICA_PAT="mica_pat_xxxxxxxx_yyyyyyyyyyyyyyyyyyyyyyyy"

# 只读巡检：筛出待审批（submitted）的 PR
curl -sS "$MICA_BASE/api/v1/purchase-requisitions" \
  -H "Authorization: Bearer $MICA_PAT" \
  | jq '[.[] | select(.status == "submitted") | {pr_number, title, total_amount}]'

# 导出数据集目录（GET，只读令牌即可）
curl -sS "$MICA_BASE/api/v1/exports" -H "Authorization: Bearer $MICA_PAT" | jq
```

### Python（httpx）

```python
import os
import time

import httpx

BASE = os.environ["MICA_BASE"]
PAT = os.environ["MICA_PAT"]

client = httpx.Client(
    base_url=BASE,
    headers={"Authorization": f"Bearer {PAT}"},
    timeout=30.0,
)


def get_json(path: str, **params) -> object:
    """带 429 退避的只读 GET。"""
    for attempt in range(4):
        response = client.get(path, params=params)
        if response.status_code == 429:
            wait = float(response.headers.get("Retry-After", 5))
            time.sleep(wait * (2**attempt) * (0.5 + 0.5 * (attempt % 2)))  # 退避 + 抖动
            continue
        if response.status_code in (401, 403):
            # 401 = 令牌失效/被撤销（重新签发）；403 = 作用域或角色不足（换令牌无用）
            raise RuntimeError(f"{response.status_code} {response.json().get('code')}")
        response.raise_for_status()
        return response.json()
    raise RuntimeError("429 persisted after retries; lower your request rate")


prs = get_json("/api/v1/purchase-requisitions")
for pr in prs[:10]:
    print(pr["pr_number"], pr["status"], pr["total_amount"])
```

要点：

- 令牌只从环境变量 / 密钥管理器读取，**不要**硬编码在源码或 notebook 里
- 401 与 403 是**不可重试**错误，直接失败并告警（重试只会浪费配额）
- 需要并发时按令牌配额限速（默认 600/min），并给长任务做断点续跑

### 给 AI Agent 的建议

Mica 当前**不提供 MCP server**，Agent 侧直接读 OpenAPI 契约即可：

1. **先读 `/api/openapi.json` 生成工具定义**——它包含全部端点、参数、schema，且随发布自动更新。不要手写工具清单，会与真实契约漂移。
2. **给令牌起可辨识的名字**：`agent-<用途>-<环境>`（例如 `agent-pr-triage-prod`）。将来在令牌列表里能一眼看出该撤销哪一个；名字也是审计日志里的线索。
3. **巡检类任务用只读令牌**。查询语义的 POST（`/search`、`/exports`、`/insights`、`/ai`、`/dashboard`）在只读令牌下依然可用，覆盖绝大多数读场景。
4. **把 `request_id` 记进日志**：每次请求失败时同时记录端点、时间戳、`code`、`request_id`。排障时管理员可以用它精确定位审计记录。
5. **按 `code` 分支，不要解析自然语言**：`api_token.invalid` 重新签发；`api_token.read_only` 说明该动作需要 `write`（先问人，不要自己升级令牌）；`api_token.rate_limited` 退避。
6. **Agent 不能给自己发令牌**：PAT 无法访问 `/auth/**`（`GET /auth/me` 除外），也不能签发超过自身权限的令牌。需要新权限时，由人类在 UI 上创建。
7. **不要把令牌放进提示词或工具输出**。模型上下文、日志、错误上报都可能留存明文。

---

## 对外稳定面

以下内容被视为**对外稳定契约**：

- **认证语义**：`Authorization: Bearer mica_pat_...`、令牌格式、401/403/429 的判定边界
- **令牌端点**：上表 6 个端点的路径、方法、状态码，以及 `ApiToken` / 创建响应的字段名与语义
- **错误标识**：`detail` / `code` / `request_id` 三字段结构，以及 `api_token.*` 系列 `code` 值
- **作用域语义**：`read` / `write` 的含义与只读白名单机制

保守承诺：

- **自本功能发布起 6 个月内，不对上述稳定面做破坏性变更。**
- 破坏性变更（改名、改语义、移除字段、改状态码）**不会**在 v1 上原地发生，而是走 **`/api/v2`**：v2 是 v1 的镜像路由，新语义在 v2 生效，v1 保持兼容期。
- **非破坏性变更随时可能发生**：新增端点、新增可选请求字段、新增响应字段。客户端必须**忽略未知字段**，不要用"字段数固定"的严格解析。
- 弃用流程：先在 v2 提供新形态并在 CHANGELOG / 本文档标注，再择期下线 v1 的旧形态。

---

## 故障排查

| 症状 | 最常见原因 | 处理 |
|---|---|---|
| **401** `not_authenticated` | 完全没带 `Authorization` 头（常见于代理/网关吞掉了请求头） | 检查请求是否真的发出了该头，以及中间层是否透传 |
| **401** `api_token.invalid` | ① 令牌被撤销或已被轮换（旧 secret 立即失效）② 已过期（`is_expired: true`）③ 复制时少了/多了字符、混入换行 ④ 请求头写成了 `Authorization: mica_pat_...`（漏 `Bearer `）⑤ 令牌串进了 URL query | 用 `GET /api/v1/me/tokens` 看 `is_active`；在 UI 上重新签发。检查请求头是否严格是 `Bearer <token>` |
| **403** `api_token.read_only` | 只读令牌调了写方法，或调了不在白名单路径前缀下的 POST | 确认该动作是否真的需要写；需要则用 `write` 令牌。查询类需求优先改用白名单内的端点 |
| **403** `api_token.path_forbidden` | 访问了 `/admin/**`、`/saml/**`、`/auth/**` 等硬边界 | 这些操作必须由人类在 UI 上完成，无 API 绕过 |
| **403** `api_token.scope_escalation` | 用只读令牌创建/轮换 `write` 令牌 | 换成权限足够的凭据（登录 JWT，或 `write` 令牌） |
| **403**（其他 detail） | 令牌本身没问题，是**用户角色/字段级权限**不足 | 找权限归属人调整角色，或换用有权限的账号签发令牌。换令牌无用 |
| **400** `api_token.too_many` | 达到 `api.token.max_per_user`（默认 10） | 撤销不用的令牌（看 `last_used_at`），或调整系统参数 |
| **429** `api_token.rate_limited` | 超过 `api.rate_limit_per_minute`（默认 600/min）；常见于并发抓取或多进程共用同一令牌 | 按 `Retry-After` 退避 + 抖动；降低并发；需要更高配额时让管理员调整系统参数 |
| 令牌在列表里但请求一直 401 | 有效期已过且 UI 未刷新状态 | 以 `is_expired` / `is_active` 字段为准，不以本地记录为准 |
| 实时通知收不到 | WebSocket 通道**不支持 PAT**（见下） | 通知走 UI；`/api/v1/ws/notifications` 目前只接受 JWT |

### 已知边界

- **WebSocket 不支持 PAT**：`/api/v1/ws/notifications` 只接受 JWT。PAT 面向请求/响应式集成；实时推送不在本次范围内。
- **多副本部署**：限流计数与 `last_used_at` 节流当前是**进程内**状态。单副本下行为如本文所述；将来若横向扩容为多副本，需要换成共享存储（如 Redis），否则实际限额会按副本数放大、`last_used_at` 更新会互相覆盖。

---

## 相关文档

- [ADR 0004 — 对外 API 认证：Personal Access Token](./adr/0004-api-personal-access-tokens.md)：为什么是 PAT、为什么只改一个认证入口、被否决的方案
- [开发者指南](./DEVELOPMENT.md)：新增对外 API 的约定（`CurrentUser` 注入、v2 变更流程、系统参数、i18n）
- [系统管理控制台](./user-manual/admin/03-system-console.md)：Admin → 系统参数界面说明
- [快速开始](./QUICKSTART.md)：把服务跑起来、拿到种子账号
