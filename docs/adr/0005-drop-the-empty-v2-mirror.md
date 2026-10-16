# ADR 0005 — 撤掉空壳 `/api/v2`，回到单一版本前缀

## 状态

已采纳 · 2026-10-16 · v1.56.3

## 背景

v1.3.0（2026-05-01，commit `2107784`）把整份 v1 路由镜像成了 `/api/v2`：

```python
api_router = APIRouter(prefix="/v1")
api_router.include_router(ui_config.router)
...                                   # 35 次 include

v2_router = APIRouter(prefix="/v2")   # 同一条列表的手工副本
v2_router.include_router(ui_config.router)
...                                   # 33 次 include
```

commit message 只有一句 `API v2: mirror all v1 routes under /v2/ prefix`：没有 ADR、没有设计说明；仓库历史与本机历史会话（6000+）里都查不到任何关于它的讨论。

移除前的实际状态：

| | v1 | v2 |
|---|---|---|
| 路径数 | 204 | 191 |
| operation 数 | 262 | 247 |

差的 13 条全是 `/insights/*` —— v2 漏挂了 `insights.router`。**"镜像"在几个月内就和本体不一样了**，而且是静默的：漏挂不报错，只让某些路径突然不存在。

同时它没有消费者：前端 `api/client.ts` 的 `baseURL` 恒为 `/api/v1`，仓库里引用 `/api/v2` 的只有测试。

## 决策

删除 `v2_router` 及其挂载，回到**单一版本前缀 `/api/v1`**。

同时把版本演进规则写进 [docs/DEVELOPMENT.md](../DEVELOPMENT.md) 与 [docs/API.md](../API.md)：

- 破坏性变更仍然**不会**在 v1 上原地发生
- 但 Mica **不预先维护空的版本前缀**：等第一个真实的破坏性变更出现时，才**先记录 ADR、再引入新前缀**
- 新前缀落地时必须同步更新 `services/api_tokens.py::relative_path()`——PAT 的边界判定按前缀剥离路径，漏改会让新前缀下的请求绕过硬边界
- 守护：`tests/test_api_tokens_api.py::test_the_v2_prefix_is_gone` 断言 `/api/v2/**` 返回 404，防止它被"顺手"加回来

## 理由

1. **无法解释的东西就是负债**。没有 ADR、没有消费者、没有冻结规则，却要求每个新增业务域都记得写两遍 `include_router`。
2. **"提前铺路"的收益是空的**。本意大概是让集成方现在就把 base URL 写成 `/v2`，将来分叉时不必改路径；但没有任何文档这么告诉集成方，前端自己也没用。而且真正分叉时变的是**语义**，客户端仍要改代码。
3. **成本是实打实的**。OpenAPI 一份 473 KB / 509 个 operation，每个端点重复出现两次。本项目的对外 API 明确面向**脚本与其他系统、AI Agent**（见 [ADR 0004](./0004-api-personal-access-tokens.md)），而 Agent 读 schema 是要花 context 的——一半是同义重复。移除后降到 310 KB。
4. **静默漂移已经发生**。13 条 `insights` 路径缺失数月无人发现，说明"两份手工列表"这种结构本身不可维护。

## 后果

### 正面

- 路径与文档各一份：schema 缩减约 34%，对接方不必再猜用哪个前缀
- 新增业务域只需 include 一次，漏挂面直接消失
- 版本策略回到可解释状态：**有真实的破坏性变更，才有新前缀**

### 负面 / 需要接受

- 若有外部集成写死了 `/api/v2`，现在会 404。已知消费者为零（前端 + 仓库内检索确认），故按"破坏性但无人使用"处理，并在 CHANGELOG 与 docs/API.md 显著标注
- 将来真要引入 v2，必须现做一遍（写 ADR + 挂载 + 改 `relative_path`），不能再用"复制一份列表"的方式

## 被否决的方案

| 方案 | 否决理由 |
|---|---|
| 保持现状 | 已被证明会静默漂移；每新增一个域就多一处漏挂风险；schema 体积翻倍 |
| 保留 v2 但加 `include_in_schema=False` | 文档干净了，但"两份 include 列表"的结构性缺陷还在，漏挂依旧没有告警 |
| 改成"一份列表循环挂两个前缀" + 守护测试 | 能消除漏挂，却把空壳版本制度化：仍然没有消费者，却要继续承担兼容承诺，`relative_path` 之类按前缀的逻辑也会继续被两份路径牵着走 |
| 现在就规划 v2 的破坏性变更内容 | 没有真实的破坏性需求。为不存在的问题先造版本，正是本次要纠正的错误 |

## 参考

- commit `2107784` — v1.3.0，v2 镜像的引入点
- [ADR 0004](./0004-api-personal-access-tokens.md) — 对外 API 认证（PAT）
- [docs/API.md](../API.md) §对外稳定面 — 对集成方的版本承诺
- [docs/DEVELOPMENT.md](../DEVELOPMENT.md) §新增对外 API 的约定 — 版本演进规则与本次教训
