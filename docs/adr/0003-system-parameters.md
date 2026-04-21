# ADR 0003 — 系统参数集中配置（v0.5）

## 状态

已采纳 · 2026-04-21 · v0.5.0 交付

## 背景

v0.4 及之前版本，业务阈值散落在代码里：

- 审批金额阈值 `¥100,000` 硬编码在 `services/approval.py`
- JWT 有效期 `480 分钟` 在 `config.py`
- SKU 异常检测窗口 `90 天` + 偏离阈值 `±20%` 在 `services/sku.py`
- 合同到期提醒 `30 天` 在 `services/contracts.py`
- 文件上传上限 `10 MB` + 分块 `1 MB` 在 `services/documents.py`
- 分页默认 `50` 在多个文件
- 审计日志默认回溯 `7 天` 在 `api/v1/admin.py`

每次想调整一个阈值（例如管理员反馈"审批阈值想改到 5 万"）都要：

1. 改代码
2. 加 Alembic migration（如果阈值关联 DB）
3. 重建镜像
4. 重新部署

这对 Mica 的 **"系统服务于人"** 理念是直接违背。

## 决策

引入 **`system_parameters` 表 + 缓存读通服务** 模式，把所有业务阈值搬到 DB，从 Admin 控制台可视化编辑。

### 数据模型

```sql
system_parameters (
  id UUID PRIMARY KEY,
  key VARCHAR(128) UNIQUE,           -- 点号命名: "approval.amount_threshold_cny"
  category systemparametercategory,  -- enum: approval/auth/sku/contract/upload/pagination/audit
  value JSONB,                        -- 当前值
  data_type VARCHAR(16),              -- int/float/bool/string/decimal
  default_value JSONB,                -- 管理员可"重置到默认"
  min_value JSONB,                    -- 边界校验
  max_value JSONB,
  unit VARCHAR(32),                   -- 显示提示: CNY/days/bytes/minutes
  description_zh TEXT,                -- UI tooltip
  description_en TEXT,
  is_sensitive BOOLEAN,               -- 敏感参数 UI 掩码（未来用）
  updated_by_id UUID,                 -- FK users.id
  created_at, updated_at
)
```

### 读路径

```python
class SystemParamsService:
    """缓存读通 + 写通失效"""
    async def get_int(self, session, key: str) -> int: ...
    async def get_decimal(self, session, key: str) -> Decimal: ...
    async def update(self, session, key, value, updated_by_id) -> SystemParameter: ...
    def invalidate(self, key: str | None = None) -> None: ...
```

调用点：`services/approval.py`、`services/sku.py`、`services/contracts.py`、`services/documents.py`、`api/v1/auth.py` 等都改为运行时从服务读，不再 import 模块常量。

### 写路径

Admin 控制台 → "系统参数"标签页：
- 按 category 折叠展示
- 每个参数显示 description_zh / description_en / key / 当前值 / 单位 / 默认值
- 类型感知编辑：`int/float/decimal` 用 `InputNumber` 带 min/max；`bool` 用 `Switch`；`string` 用 `Input`
- "重置到默认"按钮
- "已修改"徽标（value !== default_value）

每次 PUT / POST reset 写入 `audit_logs` 一条 `system_parameter.{key} changed from {old} to {new}` 记录。

### Bootstrap 层

`config.py` 里的常量保留作为 **启动时 fallback**。用途：

- 首次 `alembic upgrade` 跑完之前，如果代码启动需要某个参数（例如 JWT TTL 做 token 生成），读 `config.py` 值
- 迁移 `0003_system_parameters.py` 的 `upgrade()` 里 `bulk_insert` 14 条 seed 行时，值直接来自 `config.py` 的原硬编码数值
- 保证迁移链前的任意版本仍可工作

## 理由

### 1. 运维自治

管理员可以不求助开发者就调整业务阈值。这对 Mica 面向的小型企业场景尤其重要（IT 部门 ≤ 2 人，没有专职运维 + 开发配合机制）。

### 2. 审计友好

每次阈值改动都有时间戳 + 用户 + 前后值记录，满足内审 / ISO / 等保的可追溯要求。

### 3. 零破坏性变更

已有功能代码只是 **换了个数据源**，行为没变。旧测试全部继续通过。新增 `0003_system_parameters` 迁移向后兼容。

### 4. 成本极低

- 14 条 seed 行，DB 体积增加 < 2KB
- 内存缓存让读路径性能等价于原常量读
- 写路径极低频（管理员手动编辑），缓存失效不是瓶颈

## 后果

### 正面

- Admin 控制台现在是 **系统参数的真相源**
- 支持后续扩展：加新参数只需加一条 seed 行 + 在代码里换读源
- 各模块解耦：`services/approval.py` 不再 import `services/sku.py` 的常量

### 负面

- 启动时如果 DB 不可用，`system_params.get()` 会抛异常。已通过 `get_int_or(default)` 提供兜底签名缓解。
- 参数改动生效时间 = 缓存刷新间隔（当前写通即刷，零延迟）
- 如果新增非常量类型参数（如"工作日定义表"），需扩展 `data_type` 字段或走独立配置表

### 需关注

- **敏感参数**（如未来可能加的"LLM API Key"）不应存 `system_parameters`——有 `is_sensitive` 字段占位，但目前 14 个 seed 都是业务阈值，非密钥。密钥仍走 `.env` + `LLMModel.api_key` 加密字段。

## 实施清单

- [x] 模型 `SystemParameter` + enum `SystemParameterCategory`（`models/__init__.py`）
- [x] 迁移 `0003_system_parameters.py` 建表 + 14 条 seed
- [x] 服务 `SystemParamsService`（`services/system_params.py`）
- [x] 路由 `api/v1/system_params_admin.py`（4 个端点）
- [x] 替换 6 个文件的硬编码读取点
- [x] 前端 Admin 控制台"系统参数"Tab（`pages/admin/SystemParamsTab.tsx`）
- [x] 审计日志 hook
- [x] e2e 59/59 回归通过

## 参考

- `backend/migrations/versions/0003_system_parameters.py`
- `backend/app/services/system_params.py`
- `backend/app/api/v1/system_params_admin.py`
- `frontend/src/pages/admin/SystemParamsTab.tsx`
