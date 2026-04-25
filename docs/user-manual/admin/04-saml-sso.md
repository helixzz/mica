# SAML SSO

Mica 支持通过 SAML 2.0 接入企业身份提供方（IdP），可用于 ADFS 和 Microsoft Entra ID。

## 需要维护的关键参数

| 参数键 | 含义 |
|:---|:---|
| `auth.saml.enabled` | 是否启用 SAML 登录 |
| `auth.saml.idp.entity_id` | IdP Entity ID |
| `auth.saml.idp.sso_url` | IdP 登录地址 |
| `auth.saml.idp.slo_url` | IdP 登出地址 |
| `auth.saml.idp.x509_cert` | IdP 签名证书 |
| `auth.saml.attr.email` | 邮箱属性映射 |
| `auth.saml.attr.display_name` | 显示名属性映射 |
| `auth.saml.attr.groups` | 用户组属性映射 |

## ADFS 集成

在 ADFS 中创建新的信赖方信任，并填写：

- ACS URL：`https://<your-domain>/api/v1/saml/acs`
- Entity ID：`https://<your-domain>/api/v1/saml/metadata`

常见 ADFS 取值：

- Entity ID：`http://adfs.yourcompany.com/adfs/services/trust`
- SSO URL：`https://adfs.yourcompany.com/adfs/ls/`

## Microsoft Entra ID 集成

在 Entra ID 中创建企业应用，SAML 基本配置通常包括：

- Identifier：`https://<your-domain>/api/v1/saml/metadata`
- Reply URL：`https://<your-domain>/api/v1/saml/acs`
- Sign-on URL：`https://<your-domain>/login`

## JIT 自动建用户与组映射

可通过系统参数配置：

- 默认角色
- 默认公司编码
- 默认部门编码
- 组到角色 / 部门的自动映射 JSON

## 启用前检查

- IdP 参数已填写完整
- 签名证书为完整 PEM
- 默认公司编码有效
- IdP 端的 ACS 和 Entity ID 与 Mica 一致
