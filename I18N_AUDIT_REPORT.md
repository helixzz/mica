# Mica Backend i18n Audit Report

## Executive Summary
- **Total Issues Found**: 20 actionable items
- **Missing Keys in en-US**: 2 keys
- **Hardcoded Strings**: 16 strings in HTTPException calls
- **Dynamic Keys**: 2 keys with placeholders
- **Recently Added Files**: ✓ Clean (no hardcoded strings found)

---

## 1. MISSING KEYS IN en-US.json (Present in zh-CN.json)

### Issue 1.1: feishu.card_send_failed
- **File**: `backend/app/i18n/messages/en-US.json`
- **Status**: Missing translation
- **zh-CN Value**: "飞书卡片消息发送失败"
- **Action**: Add English translation
- **Priority**: Medium (used in notifications service)

### Issue 1.2: feishu.not_enabled
- **File**: `backend/app/i18n/messages/en-US.json`
- **Status**: Missing translation
- **zh-CN Value**: "飞书集成未启用"
- **Action**: Add English translation
- **Priority**: Medium (used in feishu integration)

---

## 2. HARDCODED HTTPException DETAIL STRINGS (Not in Locale Files)

### Issue 2.1: Security Errors (core/security.py)

#### 2.1.1 invalid_token_payload
- **File**: `backend/app/core/security.py:76`
- **Code**: `raise HTTPException(status_code=401, detail="invalid_token_payload")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files and use `t()` function
- **Priority**: High (authentication error)
- **Suggested Keys**:
  - zh-CN: "auth.invalid_token" → "登录已过期，请重新登录" (already exists)
  - en-US: "auth.invalid_token" → "Session expired, please log in again" (already exists)
  - **OR** create new keys: "auth.invalid_token_payload"

#### 2.1.2 user_not_found_or_inactive
- **File**: `backend/app/core/security.py:81`
- **Code**: `raise HTTPException(status_code=401, detail="user_not_found_or_inactive")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files and use `t()` function
- **Priority**: High (authentication error)
- **Suggested Keys**:
  - zh-CN: "auth.user_inactive" → "账号已停用" (already exists)
  - en-US: "auth.user_inactive" → "Account is inactive" (already exists)
  - **OR** create new keys: "auth.user_not_found_or_inactive"

---

### Issue 2.2: Master Data Errors (services/master_data.py)

#### 2.2.1 company.not_found
- **File**: `backend/app/services/master_data.py:510, 556, 575`
- **Code**: `raise HTTPException(status_code=404, detail="company.not_found")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: High
- **Suggested Translations**:
  - zh-CN: "公司不存在"
  - en-US: "Company not found"

#### 2.2.2 department.not_found
- **File**: `backend/app/services/master_data.py:623, 671`
- **Code**: `raise HTTPException(status_code=404, detail="department.not_found")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: High
- **Suggested Translations**:
  - zh-CN: "部门不存在"
  - en-US: "Department not found"

#### 2.2.3 department.parent_cycle
- **File**: `backend/app/services/master_data.py:140, 152, 154`
- **Code**: `raise HTTPException(status_code=409, detail="department.parent_cycle")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "部门层级存在循环引用"
  - en-US: "Department hierarchy contains a circular reference"

#### 2.2.4 department.parent_not_found
- **File**: `backend/app/services/master_data.py:144`
- **Code**: `raise HTTPException(status_code=404, detail="department.parent_not_found")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "上级部门不存在"
  - en-US: "Parent department not found"

#### 2.2.5 department.parent_company_mismatch
- **File**: `backend/app/services/master_data.py:146`
- **Code**: `raise HTTPException(status_code=409, detail="department.parent_company_mismatch")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "上级部门与当前部门所属公司不一致"
  - en-US: "Parent department belongs to a different company"

---

### Issue 2.3: Item Delete Constraints (services/master_data.py)

#### 2.3.1 item.has_po_items; hard delete denied
- **File**: `backend/app/services/master_data.py:426`
- **Code**: `raise HTTPException(status_code=409, detail="item.has_po_items; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files (consider refactoring message format)
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "该物料已被采购订单使用，无法删除"
  - en-US: "This item is referenced by purchase orders and cannot be deleted"

#### 2.3.2 item.has_pr_items; hard delete denied
- **File**: `backend/app/services/master_data.py:428`
- **Code**: `raise HTTPException(status_code=409, detail="item.has_pr_items; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "该物料已被采购申请使用，无法删除"
  - en-US: "This item is referenced by purchase requisitions and cannot be deleted"

#### 2.3.3 item.has_price_records; hard delete denied
- **File**: `backend/app/services/master_data.py:431`
- **Code**: `raise HTTPException(status_code=409, detail="item.has_price_records; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Low
- **Suggested Translations**:
  - zh-CN: "该物料已有价格记录，无法删除"
  - en-US: "This item has price records and cannot be deleted"

#### 2.3.4 item.has_price_benchmarks; hard delete denied
- **File**: `backend/app/services/master_data.py:437`
- **Code**: `raise HTTPException(status_code=409, detail="item.has_price_benchmarks; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Low
- **Suggested Translations**:
  - zh-CN: "该物料已有价格基准，无法删除"
  - en-US: "This item has price benchmarks and cannot be deleted"

#### 2.3.5 item.has_price_anomalies; hard delete denied
- **File**: `backend/app/services/master_data.py:441`
- **Code**: `raise HTTPException(status_code=409, detail="item.has_price_anomalies; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Low
- **Suggested Translations**:
  - zh-CN: "该物料已有价格异常记录，无法删除"
  - en-US: "This item has price anomalies and cannot be deleted"

#### 2.3.6 item.not_found
- **File**: `backend/app/services/master_data.py:~400`
- **Code**: `raise HTTPException(status_code=404, detail="item.not_found")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: High
- **Suggested Translations**:
  - zh-CN: "物料不存在"
  - en-US: "Item not found"

---

### Issue 2.4: Supplier Delete Constraints (services/master_data.py)

#### 2.4.1 supplier.has_pr_items; hard delete denied
- **File**: `backend/app/services/master_data.py:289`
- **Code**: `raise HTTPException(status_code=409, detail="supplier.has_pr_items; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "该供应商已被采购申请使用，无法删除"
  - en-US: "This supplier is referenced by purchase requisitions and cannot be deleted"

#### 2.4.2 supplier.has_contracts; hard delete denied
- **File**: `backend/app/services/master_data.py:292`
- **Code**: `raise HTTPException(status_code=409, detail="supplier.has_contracts; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "该供应商已有合同关联，无法删除"
  - en-US: "This supplier has associated contracts and cannot be deleted"

#### 2.4.3 supplier.has_invoices; hard delete denied
- **File**: `backend/app/services/master_data.py:295`
- **Code**: `raise HTTPException(status_code=409, detail="supplier.has_invoices; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Medium
- **Suggested Translations**:
  - zh-CN: "该供应商已有发票记录，无法删除"
  - en-US: "This supplier has invoice records and cannot be deleted"

#### 2.4.4 supplier.has_price_records; hard delete denied
- **File**: `backend/app/services/master_data.py:300`
- **Code**: `raise HTTPException(status_code=409, detail="supplier.has_price_records; hard delete denied")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: Low
- **Suggested Translations**:
  - zh-CN: "该供应商已有价格记录，无法删除"
  - en-US: "This supplier has price records and cannot be deleted"

#### 2.4.5 supplier.not_found
- **File**: `backend/app/services/master_data.py:~400`
- **Code**: `raise HTTPException(status_code=404, detail="supplier.not_found")`
- **Status**: Hardcoded, not in locale files
- **Action**: Add to both locale files
- **Priority**: High
- **Suggested Translations**:
  - zh-CN: "供应商不存在"
  - en-US: "Supplier not found"

---

## 3. DYNAMIC KEYS WITH PLACEHOLDERS

### Issue 3.1: entity_name.code_exists:{code}
- **File**: `backend/app/services/master_data.py:110`
- **Code**: `raise HTTPException(status_code=409, detail=f"{entity_name}.code_exists:{code}")`
- **Status**: Dynamic key construction, not in locale files
- **Action**: Refactor to use proper i18n with parameters
- **Priority**: Medium
- **Suggested Approach**:
  - Create keys: `{entity_name}.code_exists` (e.g., `company.code_exists`, `item.code_exists`)
  - Use: `t(f"{entity_name}.code_exists", locale, code=code)`
  - Suggested Translations:
    - zh-CN: "编码 {code} 已被占用"
    - en-US: "Code {code} is already in use"

### Issue 3.2: departments.code_exists:{code}
- **File**: `backend/app/services/master_data.py:127`
- **Code**: `raise HTTPException(status_code=409, detail=f"departments.code_exists:{code}")`
- **Status**: Dynamic key construction, not in locale files
- **Action**: Refactor to use proper i18n with parameters
- **Priority**: Medium
- **Suggested Approach**:
  - Create key: `department.code_exists`
  - Use: `t("department.code_exists", locale, code=code)`
  - Suggested Translations:
    - zh-CN: "部门编码 {code} 已被占用"
    - en-US: "Department code {code} is already in use"

---

## 4. RECENTLY ADDED FILES (Audit Results)

### ✓ sla_escalation.py
- **Status**: Clean
- **Details**: Uses proper `t()` calls with locale parameter
- **Keys Used**: 
  - `notification.sla.escalated_submitter` ✓
  - `notification.sla.escalated_submitter_body` ✓
  - `notification.sla.escalated_manager` ✓
  - `notification.sla.escalated_manager_body` ✓
  - `notification.sla.escalated_admin` ✓
  - `notification.sla.escalated_admin_body` ✓

### ✓ daily_digest.py
- **Status**: Clean
- **Details**: No hardcoded user-facing strings (HTML email body is system-generated)
- **Note**: Email subject is hardcoded but not user-facing i18n

### ✓ contract_extract.py
- **Status**: Clean
- **Details**: No hardcoded user-facing strings (error messages are system-level)
- **Note**: Prompt text is system-level, not user-facing

---

## 5. SUMMARY OF FIXES NEEDED

| Category | Count | Priority | Effort |
|----------|-------|----------|--------|
| Missing en-US keys | 2 | Medium | Low |
| Hardcoded HTTPException strings | 14 | High | Medium |
| Dynamic key placeholders | 2 | Medium | Medium |
| **Total** | **18** | - | - |

---

## 6. RECOMMENDED FIX ORDER

1. **Phase 1 (Critical)** - Security & Core Errors
   - Add `auth.invalid_token_payload` and `auth.user_not_found_or_inactive` to both locale files
   - Add `company.not_found`, `department.not_found`, `item.not_found`, `supplier.not_found` to both locale files

2. **Phase 2 (High)** - Master Data Errors
   - Add all `department.parent_*` keys to both locale files
   - Add all `*.has_*; hard delete denied` keys to both locale files

3. **Phase 3 (Medium)** - Feishu Integration
   - Add `feishu.card_send_failed` and `feishu.not_enabled` to en-US.json

4. **Phase 4 (Medium)** - Dynamic Keys Refactoring
   - Refactor `{entity_name}.code_exists:{code}` pattern to use proper i18n

---

## 7. VERIFICATION CHECKLIST

After fixes:
- [ ] All keys in zh-CN.json have corresponding keys in en-US.json
- [ ] All keys in en-US.json have corresponding keys in zh-CN.json
- [ ] All HTTPException detail strings use `t()` function
- [ ] No hardcoded error messages in `detail=` parameters
- [ ] All `t()` calls reference keys that exist in both locale files
- [ ] Run: `python3 -m pytest backend/tests/test_i18n.py` (if test file exists)

