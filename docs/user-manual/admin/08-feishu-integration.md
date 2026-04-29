# 飞书集成配置

Mica 支持将审批通知推送到飞书机器人，并支持在飞书审批流中完成付款审批。本章说明如何在飞书开放平台创建应用，以及在 Mica Admin 控制台中完成对接配置。

> ℹ️ 飞书集成是**可选功能**，默认关闭。未配置时不影响系统其他功能。

---

## 功能概览

| 能力 | 说明 | 默认状态 |
|---|---|---|
| 消息推送 | PR 提交、审批决策、PO 生成、付款待审、合同到期 → 飞书卡片通知 | 关闭 |
| 付款审批 | 在飞书审批流中创建付款审批实例，审批结果回调同步 Mica | 关闭 |

---

## 飞书权限申请（3 个最小权限）

在飞书开放平台创建企业自建应用时，**仅需开通以下 3 个权限**：

| 权限码 | 用途 |
|---|---|
| `im:message:send_as_bot` | 以机器人身份发送卡片通知 |
| `approval:instance` | 在飞书审批流中创建付款审批单 |
| `approval:approval:readonly` | 读取审批实例状态（配合回调同步） |

> 🔐 不需要开通通讯录、云文档、日历等权限。用户识别通过 email 匹配，组织架构由 Mica 自行管理。

---

## 配置步骤

### 第一步：创建飞书企业自建应用

1. 登录 [飞书开放平台](https://open.feishu.cn/) → 右上角头像 → **开发者后台**
2. 左侧导航 → **企业自建应用** → **创建企业自建应用**
3. 应用名称填写 `Mica 采购助手`，点击创建

### 第二步：获取 App ID 和 App Secret

1. 进入应用详情页 → 左侧 **凭证与基础信息**
2. 记录 **App ID**（如 `cli_xxxxxxxxxxxxx`）
3. 点击 **显示** 查看 **App Secret**，复制保存

> ⚠️ App Secret 仅在首次创建时可查看。离开页面后无法再次获取，请立即保存。

### 第三步：开通权限

1. 左侧导航 → **权限管理**
2. 在 API 权限搜索框中逐一搜索并开通上述 3 个权限码
3. 确认每个权限的状态均为 **"已开通"**

### 第四步：发布应用版本

1. 左侧导航 → **版本管理与发布**
2. 点击 **创建版本**，填写版本号（如 `1.0.0`）和更新说明
3. 保存后，在版本列表中点击 **申请发布**
4. 审批通过后状态变为 **"已发布"**

> 📌 仅需发布一次。

### 第五步：（可选）配置回调 URL

如需启用**付款审批工作流**，需配置事件订阅：

1. 左侧导航 → **事件订阅** → **配置**
2. 请求网址填入：`https://<你的域名>/api/v1/feishu/webhook`
3. 勾选事件 `approval_instance` 和 `approval_instance.cc`
4. 保存

> ⚠️ 回调 URL 必须使用公网可达的 **HTTPS** 域名。

### 第六步：在 Mica Admin 控制台填入凭证

1. 登录 Mica → **Admin 控制台** → **飞书集成** 选项卡
2. 填入 App ID、App Secret
3. 打开 **启用飞书集成** 开关
4. 按需勾选通知开关
5. 点击 **保存设置**
6. 点击 **测试连接** 按钮验证

| 字段 | 来源 |
|---|---|
| App ID | 飞书开发者后台 → 凭证与基础信息 |
| App Secret | 同上（创建时保存的字符串） |
| Approval Code | 飞书审批后台 → 审批模板详情（可选，用于付款工作流） |

### 第七步：验证

提交一个测试采购申请（PR），审批人应在飞书中收到卡片消息。如果没有收到，请检查：

- 飞书应用是否已发布（第四步）
- 3 个权限是否均为"已开通"状态（第三步）
- App ID / Secret 是否正确（无多余空格）
- 服务器是否可以访问 `open.feishu.cn`

---

## 系统参数速查

以下参数通过 Mica Admin 控制台 → 飞书集成页面统一管理，也可在系统参数表中直接查询：

| 参数键 | 类型 | 说明 |
|---|---|---|
| `auth.feishu.enabled` | bool | 总开关 |
| `auth.feishu.app_id` | string | 飞书应用 ID |
| `auth.feishu.app_secret` | secret | 飞书应用密钥 |
| `auth.feishu.notify_on_pr` | bool | PR 提交通知 |
| `auth.feishu.notify_on_approval` | bool | 审批决策通知 |
| `auth.feishu.notify_on_po` | bool | PO 生成通知 |
| `auth.feishu.notify_on_payment` | bool | 付款待审通知 |
| `auth.feishu.notify_on_contract_expiry` | bool | 合同到期通知 |
| `auth.feishu.payment_workflow` | bool | 付款审批工作流开关 |
| `auth.feishu.approval_code` | string | 飞书审批模板编码 |

---

## 相关文档

- [SAML SSO 配置](./04-saml-sso.md)
- [权限架构](./05-permissions.md)
- [故障排查与升级](./07-troubleshooting-and-upgrade.md)