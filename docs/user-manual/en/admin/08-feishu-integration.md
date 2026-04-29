# Feishu (Lark) Integration

Mica supports pushing approval notifications to Feishu bots and handling payment approvals within Feishu approval workflows. This chapter explains how to create an enterprise application in Feishu Open Platform and complete the integration in Mica Admin Console.

> ℹ️ Feishu integration is **optional** and disabled by default. It does not affect other system functions when not configured.

---

## Feature Overview

| Feature | Description | Default |
|---|---|---|
| Message Push | PR submitted, approval decided, PO created, payment pending, contract expiry → Feishu card notifications | Off |
| Payment Approval | Create payment approval instances in Feishu workflow, callback sync to Mica | Off |

---

## Required Permissions (3 Minimum)

When creating an enterprise app in Feishu Open Platform, **only 3 permissions** are needed:

| Permission Code | Usage |
|---|---|
| `im:message:send_as_bot` | Send card notifications as a bot |
| `approval:instance` | Create payment approval instances |
| `approval:approval:readonly` | Read approval status (for callback sync) |

> 🔐 Do **not** request additional permissions (contacts, drive, calendar, etc.). User matching uses email; organization structure is managed by Mica.

---

## Setup Steps

### Step 1: Create Feishu Enterprise App

1. Log in to [Feishu Open Platform](https://open.feishu.cn/) → Avatar → **Developer Console**
2. Navigation → **Enterprise Apps** → **Create Enterprise App**
3. Fill in the app name (`Mica Procurement Assistant`) and create

### Step 2: Get App ID and Secret

1. App details page → **Credentials & Basic Info**
2. Note the **App ID** (e.g. `cli_xxxxxxxxxxxxx`)
3. Click **Show** to reveal the **App Secret** and save immediately

> ⚠️ The App Secret is only visible once after creation. Save it now.

### Step 3: Enable Permissions

1. Navigation → **Permission Management**
2. Search for and enable the 3 permissions listed above, one by one
3. Confirm all 3 show as **"Granted"**

### Step 4: Publish App Version

1. Navigation → **Version Management & Release**
2. **Create Version**, fill in version number (`1.0.0`) and release notes
3. Save, then click **Apply for Release**
4. Wait for approval → status becomes **"Published"**

> 📌 Only needs to be published once.

### Step 5: (Optional) Configure Callback URL

Required only if you plan to use the **payment approval workflow**:

1. Navigation → **Event Subscription** → **Configure**
2. Request URL: `https://<your-domain>/api/v1/feishu/webhook`
3. Check events `approval_instance` and `approval_instance.cc`
4. Save

> ⚠️ The callback URL must be a publicly reachable **HTTPS** domain.

### Step 6: Configure in Mica Admin Console

1. Log in to Mica → **Admin Console** → **Feishu** tab
2. Fill in the App ID and App Secret
3. Toggle **Enable Feishu Integration** on
4. Check notification types as needed
5. Click **Save Settings**
6. Click **Test Connection** to verify

| Field | Source |
|---|---|
| App ID | Feishu Developer Console → Credentials |
| App Secret | Saved from Step 2 |
| Approval Code | Feishu Approval Admin → Template details (optional, for payment workflow) |

### Step 7: Verify

Submit a test Purchase Requisition (PR). The approver should receive a card message in Feishu. If no message arrives, check:

- App is published (Step 4)
- All 3 permissions are "Granted" (Step 3)
- App ID and Secret are correct (no extra spaces)
- The server can reach `open.feishu.cn`

---

## System Parameters Reference

These parameters are managed through Mica Admin Console → Feishu Integration tab, or directly in the system_parameters table:

| Parameter Key | Type | Description |
|---|---|---|
| `auth.feishu.enabled` | bool | Master switch |
| `auth.feishu.app_id` | string | Feishu App ID |
| `auth.feishu.app_secret` | secret | Feishu App Secret |
| `auth.feishu.notify_on_pr` | bool | PR submitted notification |
| `auth.feishu.notify_on_approval` | bool | Approval decision notification |
| `auth.feishu.notify_on_po` | bool | PO created notification |
| `auth.feishu.notify_on_payment` | bool | Payment pending notification |
| `auth.feishu.notify_on_contract_expiry` | bool | Contract expiry notification |
| `auth.feishu.payment_workflow` | bool | Payment approval workflow switch |
| `auth.feishu.approval_code` | string | Feishu approval template code |

---

## Related Documents

- [SAML SSO](./04-saml-sso.md)
- [Permission Model](./05-permissions.md)
- [Troubleshooting and Upgrade](./07-troubleshooting-and-upgrade.md)