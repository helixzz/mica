# ADR 0004 — 对外 API 认证：Personal Access Token（PAT）

## 状态

已采纳 · 2026-10-16 · 随 PAT API 一同交付（具体版本见 [CHANGELOG](../../CHANGELOG.md)）

## 背景

Mica 自 v0.1 起就有完整的 REST API（`/api/v1/*`，30+ 端点，另有一份 `/api/v2` 镜像路由）。但对外唯一可用的凭据是 **人类登录签发的 JWT**（`POST /api/v1/auth/login`，TTL 由系统参数控制）。这带来三类实际需求无法被满足：

1. **脚本与外部系统接入**。运维脚本、监控、外部报表工具需要长期稳定的凭据。用 JWT 意味着脚本必须保存**人类账号密码**去换取新 token——把人的密码复制到 N 台机器和 CI 变量里，是明确的倒退。
2. **不可撤销**。JWT 是无状态签名凭据，泄漏后无法单独作废，只能等它过期（或轮换签名密钥，那等于让所有人掉线）。这与"凭据泄漏后应当能一键止血"的安全预期直接冲突。
3. **无法回答"这个凭据是谁、用来做什么"**。一个 JWT 只代表"某人登录过"，不携带用途标签，审计里看不到"是哪台机器在用、最近还用不用"。

同时也存在反向约束——**这是一个 < 100 人、月 < 300 单的内部系统**（见 [AGENTS.md](../../AGENTS.md) §1）。它没有专职的身份平台团队，也不该为了"机器能调 API"而引入一个必须 7×24 高可用的授权服务器。

## 决策

引入 **Personal Access Token（PAT）**：绑定用户、长期有效、可撤销、可限权的机器凭据。

### 令牌形态

```
mica_pat_<prefix>_<secret>
```

- `prefix`：明文随机串，可安全展示，用于 UI 列表显示与**索引查找**
- `secret`：高熵随机串（CSPRNG），**明文只在创建/轮换响应里返回一次**
- 固定前缀 `mica_pat_` 便于密钥扫描工具识别

数据库只存 `sha256(secret)`；另存明文 `prefix` 用于展示与索引查找。数据模型（`api_tokens` 表，`backend/app/models/__init__.py`）：

| 列 | 用途 |
|---|---|
| `id` | 主键 |
| `user_id` | 绑定的用户（FK `users.id`，`ON DELETE CASCADE`） |
| `name` | 用户自取的用途标签（≤ 64 字符） |
| `token_prefix` | 明文 prefix，索引列 |
| `token_hash` | `sha256(secret)`，UNIQUE |
| `scopes` | JSONB 数组，`read` / `write` |
| `expires_at` / `revoked_at` | 过期与撤销时间戳 |
| `last_used_at` / `last_used_ip` | 最近使用线索（60 秒节流更新） |
| `created_by_id` | 创建者（管理员代建场景） |

> 命名对齐：库中列名是 `token_prefix`，**对外 API 响应字段是 `prefix`**（见 [docs/API.md](../API.md) 的响应示例）。两者指的是同一个值，接入方按 API 字段名为准。

### 校验入口只有一个

**所有端点走同一个 FastAPI 依赖 `get_current_user`（`backend/app/core/security.py`）**，在那里按 `Authorization` 头的值分流：

```
Authorization: Bearer mica_pat_...  → PAT 分支
Authorization: Bearer <其他>         → 原有 JWT 路径（行为不变）
```

因此**所有现有 REST 端点（v1 与 v2 镜像）自动支持 PAT，零业务改动**，也不需要在新端点里写任何 PAT 相关代码。

PAT 分支的校验顺序：

1. 取 `Authorization: Bearer` 的原始值；`looks_like_pat()` 判定为 `mica_pat_` 才走本分支，否则回落到原有 JWT 路径
2. 解析 `prefix`，按 `token_prefix` 索引列定位候选行
3. `sha256(secret)` 与 `token_hash` 做**常量时间**比对（`hmac.compare_digest`）
4. 拒绝已撤销（`revoked_at` 非空）或已过期（`expires_at` 已过）的令牌 → 401 `api_token.invalid`
5. 以 60 秒窗口节流更新 `last_used_at` / `last_used_ip`
6. 按令牌限流 → 429 `api_token.rate_limited` + `Retry-After`
7. 硬边界路径检查（`/admin/**`、`/saml/**`、`/auth/**`，仅放行 `GET /api/v1/auth/me`）→ 403 `api_token.path_forbidden`
8. 作用域检查：`read` 令牌的非只读方法，除只读 POST 白名单外 → 403 `api_token.read_only`
9. 若 `api.audit_requests` 打开，写一条请求级审计
10. 返回该用户的 `User` 行，并把令牌上下文（`api_token` / `api_token_scopes`）挂到 `request.state`，供下游使用——"不能签发权限超过自身的令牌"这条约束就取这里的 scope 上限

上述判定之后的一切**没有任何 PAT 特例**：`require_roles(...)`、行级过滤（`core/scoping.py`）、Cerbos 字段级权限都按原来的代码路径执行。换句话说，**PAT 只是"换了一种凭据证明你是谁"，不改变"你能做什么"的判定链**。

### 权限模型：用户权限 ∩ 令牌作用域

| 层 | 来源 | 作用 |
|---|---|---|
| 角色权限 | 令牌所属用户的 `role` / `department_id` | 主权限来源，与 UI 登录完全一致 |
| 令牌作用域 | `read` / `write` | 在此基础上**收窄**，不能放大 |

- `read`：只读。非只读方法返回 403（只读 POST 白名单除外）
- `write`：读写。**不等于超管**——用户角色不允许的操作依然被拒

### 三条硬边界 + 不可自我提权

| 边界 | 覆盖 | 理由 |
|---|---|---|
| `/admin/**` | 系统参数、用户/角色、审计日志 | 管理面是"权限的定义者" |
| `/saml/**` | SAML 断言消费 | 身份面是"身份的建立过程" |
| `/auth/**` | 登录/注册/凭据签发（仅放行 `GET /api/v1/auth/me`） | 凭据面是"凭据的签发者" |
| 不可自我提权 | 只读 PAT 不能签发 `write` 令牌；任何 PAT 不能创建超出自身权限的令牌 | 否则作用域收窄形同虚设 |

即：**管理类与凭据类操作必须由人类在 UI 上完成。**

### 可配置项（`system_parameters`，category `api`）

| Key | 默认 | 说明 |
|---|---|---|
| `api.token.max_per_user` | 10 | 每用户令牌数上限 |
| `api.token.default_ttl_days` | 90 | 默认有效期 |
| `api.token.max_ttl_days` | 365 | 最长有效期 |
| `api.rate_limit_per_minute` | 600 | 每令牌每分钟请求上限 |
| `api.audit_requests` | false | 是否逐请求写审计 |
| `api.read_only_post_allowlist` | `/search`、`/exports`、`/insights`、`/ai`、`/dashboard` | 只读令牌下仍允许的 POST 路径前缀 |

遵循 [ADR 0003](./0003-system-parameters.md)：**没有任何阈值硬编码在代码里**，管理员在 Admin → 系统参数中可视化调整，无需重新部署。

### 审计

- 令牌生命周期（创建 / 轮换 / 撤销）**总是**写 `audit_logs`，可通过 `GET /api/v1/admin/audit-logs` 查询
- 逐请求审计默认**关闭**（`api.audit_requests=false`）：内部系统若把每次读请求都落审计表，写入量会不成比例地放大。需要完整留痕的窗口期再打开
- `last_used_at` / `last_used_ip` 以 60 秒节流更新，用于识别"还在用/已废弃"的令牌

### 对外端点

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/me/tokens` | 列出我的令牌（仅元数据） |
| `POST` | `/api/v1/me/tokens` | 创建，→ 201，响应含一次性明文 `token` |
| `POST` | `/api/v1/me/tokens/{id}/rotate` | 轮换，→ 201；旧令牌立即失效 |
| `DELETE` | `/api/v1/me/tokens/{id}` | 撤销，→ 204 |
| `GET` | `/api/v1/admin/api-tokens` | 全站列表（admin），支持 `user_id` / `include_revoked` / `limit` / `offset` |
| `DELETE` | `/api/v1/admin/api-tokens/{id}` | 强制撤销（admin），→ 204 |

错误统一返回 `detail` / `code` / `request_id`，`code` 取值形如 `api_token.invalid`、`api_token.read_only`、`api_token.rate_limited`、`api_token.too_many`。

## 理由

### 1. 为什么是 PAT，而不是"再发一种 JWT"

PAT 与 JWT 的本质差别不是格式，而是**状态**：

| 维度 | 长期 JWT | PAT |
|---|---|---|
| 撤销 | ❌ 不可能（只能等过期 / 轮换签名密钥） | ✅ 一行 DB 状态，立即生效 |
| 用途标识 | ❌ 只有"某人" | ✅ 名称 + prefix，可辨识"是哪条流水线" |
| 权限收窄 | ❌ 与人类登录同权 | ✅ `read` / `write` 作用域 |
| 使用可见性 | ❌ 无 | ✅ `last_used_at` / `last_used_ip` |
| 泄漏影响面 | 该用户全部权限，直到过期 | 该用户权限 ∩ 作用域，撤销即止血 |

"可撤销"是这里压倒性的理由。机器凭据一定会被复制到 CI、容器、同事的笔记本上；能不能一键作废，决定了事故是"改一个状态"还是"全站重新登录"。

### 2. 为什么只改一个认证依赖入口

把所有 PAT 逻辑收进 `get_current_user`，而不是在端点里加分支，带来三个直接收益：

1. **零业务回归面**。30+ 端点文件、v1 + v2 两套镜像，一行业务代码都没动；PAT 的能力边界由**一个函数**决定。
2. **未来端点自动继承**。新端点只要按既有约定注入 `CurrentUser`（见 [DEVELOPMENT.md](../DEVELOPMENT.md) 的"新增对外 API 的约定"），就自动获得 PAT 支持、硬边界、作用域与限流。不存在"新端点忘了适配 PAT"这类静默缺口。
3. **单一审查点**。硬边界、作用域、限流、`last_used` 节流全部在一处，安全审查与后续演进（例如把限流搬到 Redis）只需改一处。

反过来看：如果每个端点自己解析 PAT，那么"某天有人新加了一个 `/admin/xxx` 端点但忘了加 PAT 拦截"就是必然会发生的事故。**把安全约束放在公共依赖里，是让它无法被遗忘的唯一方式。**

### 3. 为什么只读 POST 白名单必须存在

纯按 HTTP 方法判定"只读"，在这个代码库里会误伤一大片**查询语义的 POST**：搜索、导出、洞察、AI、仪表盘这些路径按 HTTP 语义选了 POST（复杂筛选体、流式响应、规避超长 query），但它们不写业务数据。

如果一刀切，最典型的巡检场景（导出报表、问 AI、拉仪表盘数据）就都需要 `write` 令牌——这会让管理员被迫给只读脚本发写权限，**结果比不做白名单更不安全**。

因此：白名单只覆盖已知的查询语义路径前缀，且**由系统参数控制**（`api.read_only_post_allowlist`），管理员可增删而无需重新部署。默认保守——新路径必须被显式加入白名单才放行。

### 4. 为什么必须有那三条硬边界

三条边界对应三类"权限的定义者"，PAT 一旦够到它们就会出现自指闭环：

- **`/admin/**`**：系统参数里就存着 `api.token.max_per_user`、`api.rate_limit_per_minute`、`api.read_only_post_allowlist`。如果 PAT 能改系统参数，令牌就能改写约束自己的规则——包括把只读白名单拉满。
- **`/auth/**`、`/saml/**`**：这些端点负责建立身份与签发凭据。允许 PAT 走进去，等于允许机器**自己建立身份、自己签发凭据**，"令牌权限不超过人"的前提当场失效。
- **不可自我提权**：即使前三条都堵住了，如果只读 PAT 能签发 `write` 令牌，`read → write` 仍然只要一次调用。这条是作用域机制成立的**前提**，不是补充。

代价是接受"机器不能给自己续期、不能给自己加权限"——需要人工在 UI 上操作。这正是想要的结果：权限的每一次扩张都留下人类的痕迹。

### 5. 为什么存 `sha256(secret)` 而不是 bcrypt

这是本 ADR 里最容易被质疑的一条，理由是**两个事实的组合**，不是"sha256 更安全"：

1. **PAT 是高熵随机 secret**，不是人选的口令。bcrypt / argon2 这类慢哈希的核心价值是抵抗"低熵口令的离线爆破"；面对 128 位以上随机串，慢哈希带来的边际收益接近于零。
2. **校验发生在每一个 API 请求的认证热路径上**。bcrypt（cost 12）单次约 100ms 量级的 CPU 开销，乘以每个请求、并发 worker 数，会成为一个自制的限流器；sha256 是微秒级，认证开销可以忽略。

因此选择 `sha256` + **常量时间比较**（避免通过比较耗时泄漏前缀匹配信息）。

必须同时接受的代价与前提：

- secret 的熵**必须**由生成端保证（CSPRNG，例如 `secrets.token_urlsafe`）。若 secret 可预测，无盐 hash 就等于可查表。
- 无盐意味着同一 secret 在任何环境产生同一 hash；对随机 secret 而言不构成现实风险，但**不能**把这个 hash 当作跨环境的稳定标识来用。
- 若将来 secret 长度/熵被下调，这个决策必须重新评估——**它成立的前提是高熵，不是 sha256 本身**。

### 6. 为什么 `last_used` 要节流 60 秒

`last_used_at` / `last_used_ip` 的用途是**运维线索**（"这个令牌还有人用吗？不用就撤掉"），不是取证。如果每个请求都写一次这两列，等于给每个 API 调用加一次写事务——读接口被写入放大拖慢，而换来的精度对上述用途毫无意义。60 秒节流让"僵尸令牌清理"这件事可用，同时把写入量压到可忽略。

需要精确链路时，正确做法是打开 `api.audit_requests`，而不是提高 `last_used` 的精度。

## 后果

### 正面

- **零业务改动获得机器认证**：所有现有端点（v1 + v2 镜像）自动支持 PAT；新端点按既有约定注入 `CurrentUser` 即自动继承
- **可撤销、可收窄、可审计**：撤销即时生效；`read`/`write` 作用域限制爆炸半径；生命周期事件进 `audit_logs`
- **管理员自助运维**：6 个 `api.*` 系统参数覆盖配额、TTL、限流、审计开关与白名单，改配置不需要重新部署
- **对 AI Agent 友好**：`/api/openapi.json` 就是完整契约，Agent 可自行生成工具定义；只读令牌 + 白名单让只读巡检成为默认姿势
- **与既有权限体系零分叉**：角色、行级过滤、Cerbos 字段级权限全部沿用原路径，不存在"PAT 专用权限判定"这种第二套真相

### 负面 / 需关注

- **WebSocket 不支持 PAT**：`/api/v1/ws/notifications` 只接受 JWT（它自己解析 token，不走 `get_current_user`）。因此实时推送通道无法用 PAT 接入；若要支持，需要为 WS 单独设计一次认证握手，而不是复用本文的机制。
- **限流与 `last_used` 节流是进程内状态**：单副本部署下语义正确；**多副本部署时必须换成共享存储（如 Redis）**，否则每副本各自计数会让实际限额放大到 N × `api.rate_limit_per_minute`，`last_used_at` 也会被不同副本互相覆盖。
- **明文不可找回**：丢失只能轮换。这是刻意的（服务端没有明文可给），代价是接受"轮换"作为唯一恢复路径。
- **无盐 hash 的前提是 secret 高熵**：见理由 §5，这是一个必须由生成端持续保证的假设。
- **多了一个需要被运维关注的实体**：僵尸令牌需要定期清理（可用 `last_used_at` 判断）。已通过 `api.token.max_per_user=10` 与列表字段把这件事变得可操作，但它不会自动发生。

## 被否决的方案

| 方案 | 否决理由 |
|---|---|
| **OAuth2 client credentials / 自建授权服务器** | 需要新增一个必须高可用的组件 + 客户端注册管理 + 授权/同意流程。Mica 的规模（< 100 人、单公司、单实例）下，机器身份的真实需求只是"可撤销的长效凭据"，一个授权服务器的运维成本远超收益。PAT 用一张表 + 一个依赖覆盖同样场景。 |
| **服务账号（bot 用户）** | 需要在 `users` 表里造影子用户，破坏"行级过滤依据真实人的 department / role"这一语义；审计里的人名会变成机器人，责任归属断链；还要额外处理这类账号的登录、密码、禁用逻辑。 |
| **长期 JWT 代替 PAT** | 不可撤销是硬伤：泄漏后只能等到过期，或轮换签名密钥（等于让全体用户重新登录）。也无法表达"用途"与"权限收窄"。 |
| **PAT 支持 WebSocket** | WS 不走 `get_current_user`，要做就得在握手处复制一遍硬边界/作用域/限流逻辑——正是决策 §2 要避免的"第二套判定路径"。本次范围内明确不支持，实时推送继续只认 JWT。 |
| **PAT 支持 URL query 传参（`?token=`）** | 令牌会进入 Nginx access log、浏览器历史、`Referer`、错误上报与各类中间件。只接受 `Authorization: Bearer` 请求头。 |
| **细粒度字段级 scope**（例如 `pr:read` / `po:write`） | Mica 的字段级与行级权限已经由角色 + Cerbos + `core/scoping.py` 表达，是**单一真相源**。再叠一层 scope 维度会产生两套权限语言，需要维护映射矩阵，并让"为什么这个请求被拒"变成组合题。当前只保留 `read` / `write` 两档，把复杂度留给已有的权限体系。 |
| **MCP server** | 先不做。Agent 侧读 `/api/openapi.json` 即可生成完整工具定义，无需再维护一个协议适配层与它的版本同步问题。若将来 Agent 生态确需 MCP，它应当是 OpenAPI 之上的一层薄封装，而不是另一套认证与授权实现。 |

## 参考

- `backend/app/core/security.py` — 唯一认证入口 `get_current_user`（JWT / PAT 分流）
- `backend/app/models/__init__.py` — `ApiToken` 模型（`api_tokens` 表）
- `backend/app/core/scoping.py`、`backend/app/core/cerbos_client.py` — 行级 / 字段级权限（PAT 请求同样经过）
- [docs/API.md](../API.md) — 对外接入指南（含 6 个端点的字段级契约、稳定面承诺、故障排查）
- [docs/DEVELOPMENT.md](../DEVELOPMENT.md) — "新增对外 API 的约定"
- [ADR 0003 — 系统参数集中配置](./0003-system-parameters.md) — `api.*` 参数的承载机制
- [AGENTS.md](../../AGENTS.md) §5.2 — 每个端点注入 `user: CurrentUser` 的既有约定
