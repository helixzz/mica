# 管理员指南

本章面向**系统管理员**——负责部署、配置和维护 Mica 系统的人员。普通业务用户无需阅读本章。

---

## 部署与启动

### 环境要求

- Docker 24+ 和 Docker Compose v2
- 至少 2GB 空闲内存
- 端口 8900（Web 入口）可用

### 首次启动

```bash
cd deploy
./scripts/dev-up.sh
```

约 60-120 秒后系统就绪。访问 `http://<服务器地址>:8900`。

### 运维脚本

| 脚本 | 功能 |
|:---|:---|
| `./scripts/health.sh` | 一键健康检查 |
| `./scripts/backup.sh` | 备份数据库和文件 |
| `./scripts/restore.sh <归档文件>` | 从备份恢复（需确认） |
| `./scripts/upgrade.sh` | 升级：自动备份 → 构建 → 迁移 → 健康检查（失败自动回滚） |
| `./scripts/logs.sh backend` | 查看容器日志 |

---

## 系统管理控制台

以管理员账号登录后，左侧导航栏最下方有 **系统管理**。

### 系统参数

可在线编辑的运行时配置，无需改代码或重启服务：

- 审批金额阈值
- JWT 令牌有效期
- SKU 基准价窗口天数
- 合同到期提醒天数
- 上传文件大小限制
- 付款到期默认天数
- 等共 15+ 项

### SAML SSO 单点登录配置（v0.8.1+）

Mica 支持通过 SAML 2.0 协议接入企业身份提供商（IdP），实现单点登录。以下说明如何对接 **ADFS** 和 **Microsoft Entra ID**（原 Azure AD）。

所有配置均在 **系统管理 → 系统参数** 中完成，无需修改配置文件或重启服务。

#### 概览：需要配置的参数

| 参数键 | 含义 | 必填 |
|:---|:---|:---|
| `auth.saml.enabled` | 是否启用 SAML SSO 登录 | 是（最后开启） |
| `auth.saml.idp.entity_id` | IdP 的 Entity ID / 颁发者标识 | 是 |
| `auth.saml.idp.sso_url` | IdP 的 SSO 登录地址 | 是 |
| `auth.saml.idp.slo_url` | IdP 的单点登出地址 | 否 |
| `auth.saml.idp.x509_cert` | IdP 签名证书（PEM 格式） | 是 |
| `auth.saml.sp.entity_id` | Mica 作为 SP 的 Entity ID | 否（自动推导） |
| `auth.saml.sp.acs_url` | Mica 的 ACS 回调地址 | 否（自动推导） |
| `auth.saml.attr.email` | 邮箱属性名 | 否（有默认值） |
| `auth.saml.attr.display_name` | 显示名属性名 | 否（有默认值） |
| `auth.saml.attr.groups` | 用户组属性名 | 否（组映射时需要） |
| `auth.saml.jit.default_role` | 自动创建用户的默认角色 | 否（默认 requester） |
| `auth.saml.jit.default_company_code` | 自动创建用户的默认公司编码 | 否 |
| `auth.saml.group_mapping_enabled` | 是否启用组→角色自动映射 | 否 |
| `auth.saml.group_mapping` | 组映射规则 JSON | 否 |

#### 方案 A：对接 ADFS (Active Directory Federation Services)

**前置条件**：Windows Server 上已安装并配置 ADFS，可以访问 ADFS 管理控制台。

##### 第 1 步：在 ADFS 中添加信赖方信任

1. 打开 **ADFS 管理** → **信赖方信任** → **添加信赖方信任**
2. 选择 **声明感知** → **手动输入信赖方数据**
3. 显示名称填 `Mica`
4. 跳过令牌加密证书（Mica 不要求加密）
5. 配置 URL：
   - 勾选 **启用对 SAML 2.0 WebSSO 协议的支持**
   - 信赖方 SAML 2.0 SSO 服务 URL 填：`https://<your-mica-domain>/api/v1/saml/acs`
6. 信赖方信任标识符（Entity ID）填：`https://<your-mica-domain>/api/v1/saml/metadata`
   - 点击 **添加**
7. 访问控制策略选 **允许所有人**（或按需选择）
8. 完成向导

##### 第 2 步：配置 ADFS 声明规则

编辑刚创建的信赖方信任 → **颁发转换规则** → 添加以下规则：

**规则 1 — 发送 LDAP 属性**（类型：以声明方式发送 LDAP 属性）
- LDAP 属性 → 传出声明类型：
  - `E-Mail-Addresses` → `E-Mail Address`
  - `Display-Name` → `Name`
  - `Token-Groups - Unqualified Names` → `Group`（如需组映射）

**规则 2 — 转换 NameID**（类型：转换传入声明）
- 传入声明类型：`E-Mail Address`
- 传出声明类型：`Name ID`
- 传出名称 ID 格式：`电子邮件`

##### 第 3 步：获取 ADFS 参数

| 需要的值 | 在哪里找 |
|:---|:---|
| Entity ID | 通常是 `http://adfs.yourcompany.com/adfs/services/trust` |
| SSO URL | 通常是 `https://adfs.yourcompany.com/adfs/ls/` |
| SLO URL | 通常是 `https://adfs.yourcompany.com/adfs/ls/?wa=wsignout1.0` |
| X.509 证书 | ADFS 管理 → 服务 → 证书 → 令牌签名 → 查看证书 → 详细信息 → 复制到文件（Base-64 编码 .cer） |

用文本编辑器打开导出的 `.cer` 文件，复制 `-----BEGIN CERTIFICATE-----` 和 `-----END CERTIFICATE-----` 之间的内容（含这两行）。

##### 第 4 步：在 Mica 中填写参数

进入 **系统管理 → 系统参数**，搜索 `auth.saml`，依次填写：

```
auth.saml.idp.entity_id = http://adfs.yourcompany.com/adfs/services/trust
auth.saml.idp.sso_url   = https://adfs.yourcompany.com/adfs/ls/
auth.saml.idp.slo_url   = https://adfs.yourcompany.com/adfs/ls/?wa=wsignout1.0
auth.saml.idp.x509_cert = -----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJ...（实际证书内容）
-----END CERTIFICATE-----
```

属性映射（ADFS 默认值通常可用）：

```
auth.saml.attr.email        = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress
auth.saml.attr.display_name = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name
auth.saml.attr.groups       = http://schemas.xmlsoap.org/claims/Group
```

#### 方案 B：对接 Microsoft Entra ID（原 Azure AD）

**前置条件**：拥有 Entra ID 租户的全局管理员或应用程序管理员权限。

##### 第 1 步：在 Entra ID 中创建企业应用程序

1. 登录 [Entra ID 管理中心](https://entra.microsoft.com)
2. 导航到 **企业应用程序** → **新建应用程序** → **创建自己的应用程序**
3. 名称填 `Mica`，选择 **集成未在库中找到的其他应用程序**
4. 创建后，进入该应用 → **单一登录** → 选择 **SAML**

##### 第 2 步：配置 SAML 基本设置

在 **基本 SAML 配置** 中编辑：

| 字段 | 值 |
|:---|:---|
| 标识符 (Entity ID) | `https://<your-mica-domain>/api/v1/saml/metadata` |
| 回复 URL (ACS) | `https://<your-mica-domain>/api/v1/saml/acs` |
| 登录 URL | `https://<your-mica-domain>/login` |

##### 第 3 步：配置属性和声明

点击 **属性和声明** → **编辑**，确保以下声明存在：

| 声明名称 | 源属性 |
|:---|:---|
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | user.mail |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name` | user.displayname |

如需组映射，额外添加组声明：
- 点击 **添加组声明** → 选择 **安全组** → 源属性选 **显示名称**

##### 第 4 步：下载证书和获取参数

在应用的 **SAML 签名证书** 区域：
- 下载 **证书 (Base64)**

在 **设置 Mica** 区域可以看到：
- **登录 URL** → 对应 `auth.saml.idp.sso_url`
- **Microsoft Entra 标识符** → 对应 `auth.saml.idp.entity_id`
- **注销 URL** → 对应 `auth.saml.idp.slo_url`

##### 第 5 步：在 Mica 中填写参数

```
auth.saml.idp.entity_id = https://sts.windows.net/<tenant-id>/
auth.saml.idp.sso_url   = https://login.microsoftonline.com/<tenant-id>/saml2
auth.saml.idp.slo_url   = https://login.microsoftonline.com/<tenant-id>/saml2
auth.saml.idp.x509_cert = -----BEGIN CERTIFICATE-----
MIIC8DCCAdigAwIBAgIQ...（Entra ID 下载的 Base64 证书内容）
-----END CERTIFICATE-----
```

属性映射（Entra ID 默认值）：

```
auth.saml.attr.email        = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress
auth.saml.attr.display_name = http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name
auth.saml.attr.groups       = http://schemas.microsoft.com/ws/2008/06/identity/claims/groups
```

> **注意**：Entra ID 默认发送组的 Object ID 而非显示名称。如果用显示名称做映射，请确保在 Entra ID 的组声明配置中选择了 **显示名称** 作为源属性。

##### 第 6 步：分配用户

在 Entra ID 企业应用的 **用户和组** 页面，添加需要 SSO 登录 Mica 的用户或用户组。

#### 通用配置：自动创建用户 (JIT)

首次通过 SSO 登录的用户，如果本地不存在，Mica 会自动创建账号。控制行为的参数：

```
auth.saml.jit.default_role          = requester
auth.saml.jit.default_company_code  = DEMO
auth.saml.jit.default_department_code =     （留空则不分配部门）
```

#### 通用配置：用户组→角色自动映射（可选）

开启后，系统根据 IdP 传回的用户组信息自动分配角色和部门：

```
auth.saml.group_mapping_enabled = true
auth.saml.group_mapping = [
  { "group": "IT-Procurement", "role": "it_buyer", "department_code": "IT" },
  { "group": "Finance", "role": "finance_auditor", "department_code": "FIN" },
  { "group": "Procurement-Managers", "role": "procurement_mgr" },
  { "group": "Department-Heads", "role": "dept_manager" }
]
```

映射按数组顺序匹配，命中第一条即停止。未命中任何规则的用户回退到 `jit.default_role`。

#### 最后一步：启用 SSO

确认以上参数都配置正确后：

```
auth.saml.enabled = true
```

刷新登录页面，应看到 **通过 SSO 登录** 按钮优先展示。本地登录入口仍可通过点击"使用本地账号登录"链接访问。

!!! tip "启用前自检清单"
    - [ ] `auth.saml.idp.entity_id` 已填写且与 IdP 端一致
    - [ ] `auth.saml.idp.sso_url` 已填写且可访问
    - [ ] `auth.saml.idp.x509_cert` 已粘贴完整 PEM 证书（含 BEGIN/END 行）
    - [ ] `auth.saml.jit.default_company_code` 指向一个已存在的公司编码
    - [ ] 在 IdP 端已正确配置 Mica 的 ACS URL 和 Entity ID

!!! warning "默认角色"
    当组映射未开启，或用户组没有命中任何规则时，系统会把自动创建的用户分配为最低权限默认角色（当前为 `requester`）。管理员可在用户管理中手动调整。

### 分类管理

维护三个分类维度，所有采购申请和物料都会引用：

| 维度 | 说明 | 示例 |
|:---|:---|:---|
| **成本中心** | 费用归属单位 | IT 部、行政部、产品部 |
| **开支类型** | 资本性 vs 运营性 | CapEx、OpEx |
| **采购种类** | 2 级层级分类 | 服务器配件 → 内存 / SSD / CPU |

### LLM 模型配置

Mica 支持接入 AI 大语言模型（用于表单润色、发票识别等）。在 **LLM 模型** Tab 可以：

1. 添加 OpenAI 兼容的第三方服务（DeepSeek / GLM / Kimi / 通义等）
2. 填写 Provider（`openai`）、Model String（如 `zai-org/glm-4.7`）、API Base 和 Key
3. 点击 **测试连接** 验证配置
4. 在 **AI 场景路由** Tab 将具体功能（表单润色、SKU 推荐）绑定到模型

!!! warning "Reasoning 模型注意"
    GLM 4.7 等推理模型会用大量 token 在"思考"上。如果 AI 返回空内容，请在路由配置中把 `max_tokens` 调高到 2000 以上。

### 用户管理

管理系统用户的角色分配和账号状态。

### 审计日志

所有关键操作（创建、审批、付款、删除）的完整记录，不可篡改，用于合规审计。

---

## 权限架构

Mica 使用三层权限控制：

1. **角色级**：不同角色看到不同的菜单和功能按钮
2. **字段级**：同一条记录中，不同角色可见的字段不同（由 Cerbos 策略引擎控制）
3. **行级**：用户只能看到自己部门/公司的数据

权限策略文件位于 `deploy/cerbos-policies/`，修改后 Cerbos 容器自动热加载，无需重启。

---

## 数据备份与恢复

### 自动备份

建议配置 crontab 定时备份：

```bash
# 每天凌晨 2 点备份
0 2 * * * cd /path/to/mica/deploy && ./scripts/backup.sh >> /var/log/mica-backup.log 2>&1
```

### 手动恢复

```bash
cd deploy
./scripts/restore.sh backups/mica-backup-20260422.tar.gz --yes-i-know
```

恢复会**覆盖当前数据库**，请谨慎操作。

---

## 故障排查

| 症状 | 排查方向 |
|:---|:---|
| 登录后白屏 | 浏览器 F12 → Network，检查 `/api/v1/auth/me` 是否 200 |
| 端口被占用 | 修改 `deploy/.env` 的 `HTTP_PORT` |
| 数据库迁移失败 | `docker compose logs migrate` 查看报错 |
| AI 返回空内容 | 检查 Admin → LLM 模型 → 测试连接；调高路由的 max_tokens |
| 通知不推送 | 检查 Admin → 系统参数 → 通知相关配置是否启用 |

---

## 版本升级

```bash
cd deploy
./scripts/upgrade.sh
```

升级脚本会自动：备份当前数据 → 拉取新镜像 → 运行数据库迁移 → 健康检查。如果任何步骤失败，自动回滚到升级前状态。
