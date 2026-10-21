# PR/PO Delivery Address Book

## Objective

Replace the single free-text `delivery_address` input on Purchase Requisition
create/edit with a dropdown that either picks a saved address book entry or
accepts a hand-typed one. An address carries three fields: contact name,
contact phone, and detailed address.

## Status

**Released and deployed as v1.57.0 (2026-10-16). Done.**

- Branch `feat/pr-delivery-address-book` (worktree `../mica-feat-address-book`),
  merged into `main` with `--no-ff` as `aaf450f`.
- Release commit `d7528a1 chore(release): bump version to 1.57.0` — the four
  version files plus `CHANGELOG.md` only, as §8 requires.
- Pushed `bd84f21..d7528a1` to `origin/main`.
- Release: https://github.com/helixzz/mica/releases/tag/v1.57.0 (target
  `d7528a1e37192a7a14fa2551cf0be3cb339d3fce`).
- Deployed with `./deploy/scripts/upgrade.sh --tag v1.57.0`; 167s, backup at
  `deploy/backups/mica-20261016-171221-a662921-1382371.tar.gz`.

Post-deploy verification against production:

| Check | Result |
|---|---|
| `/health` | `{"status":"healthy","version":"1.57.0","checks":{"db":true,"cerbos":true}}` |
| `alembic_version` | `0060` |
| `delivery_addresses` columns | 12 |
| PR / PO `delivery*` columns | 4 each |
| `/api/v1/delivery-addresses`, `/api/v2/...` | 401 (registered, auth required) |
| `POST` unauthenticated | 401 |
| Frontend `/` | 200 |
| Existing endpoints (PR, `/me/tokens`, `/ui-config`) | 401 — unaffected |

`upgrade.sh` was verified before use. The note in `PROJECT_STATE.md` that it
"may invoke destructive DB restoration" is only true on the failure path, where
`trap rollback` calls `restore.sh`; the success path never touches it. It does
still `git checkout "$TAG" -- .`, so the production checkout's HEAD stays at
`a662921` while the working tree holds the tag — that is why `git status` there
looks dirty and why the script prints `to: a662921 (v1.57.0)`.

The worktree and branch can be removed once this is reviewed:

```bash
git worktree remove ../mica-feat-address-book && git branch -d feat/pr-delivery-address-book
```

### Follow-up: collapsed control leads with the label (v1.58.1, 2026-10-16)

Reported after release: the address picker's collapsed control showed
`recipient · street address`, and a street address is far too long for a
single-line control — it was truncated into something that no longer identified
the entry, e.g. `李彦灏 · 上海市浦东新区世纪大道1196号…`.

The label is the name the user gave that address, so it is what actually
identifies the entry at a glance. The collapsed value now reads
`<label> · <recipient>`, falling back to `<recipient> · <street>` when an entry
has no label.

**The trap:** `optionFilterProp="label"` meant the displayed string *was* the
search key. Changing it would silently narrow search — looking an address up by
its street or phone number would stop working. The fix separates the two: the
label drives display only, and `filterOption` matches the whole entry (label,
recipient, phone, street).

Verified in a browser: collapsed reads `上海办公室 · 李彦灏`; searching
`乌兰察布` still finds the unlabelled Ulanqab entry and the phone number still
finds the Shanghai one. Three component tests pin this (9 in that file, 96
overall).

**Deliberately left alone:** the dropdown rows still lead with the recipient
(`李彦灏 上海办公室`). The two differ because their jobs differ — when scanning
several candidates the recipient is the main discriminator, while the collapsed
control only has to confirm a choice already made. Confirmed with the user.

### Earlier blocking note (resolved)

Local `main` HEAD was `26c317c` (v1.55.1) while the shared worktree carried an
uncommitted PAT / API-token feature touching 12 of this workstream's files,
including all four version files and migration `0059`. Starting then would have
interleaved two features in one worktree and made either one impossible to
commit, revert, or release cleanly.

A worktree was used rather than a plain `git checkout -b` because the worktree
is shared: switching branches would have dragged the other workstream's
uncommitted changes along and lifted them off `main`.

## Reserved identifiers

| Resource | Reserved value | Reason |
|---|---|---|
| Alembic revision | `0060`, `down_revision = "0059"` | PAT holds `0059` |
| Application version | `1.57.0` | PAT holds `1.56.0` |

Reserve, do not claim early. If another workstream takes `0060` first, renumber
and fix `down_revision` before writing the file.

## Baseline and overlap

Nearest local commit `26c317c` (v1.55.1). Files the PAT workstream already
modified, all of which this workstream must also touch:

| File | PAT change | This workstream |
|---|---|---|
| `backend/app/models/__init__.py` | +35 (ApiToken) | add DeliveryAddress + 3 PR cols + 3 PO cols |
| `backend/app/api/__init__.py` | +5 (router) | register address book router |
| `backend/app/config.py` | version | version |
| `backend/pyproject.toml` | version | version |
| `frontend/package.json` | version | version |
| `README.md` | version badge | version badge |
| `CHANGELOG.md` | +22 | add entry |
| `frontend/src/api/index.ts` | +66 | add address types |
| `frontend/src/i18n/locales/{zh-CN,en-US}/common.json` | +44 each | add keys |
| `backend/app/i18n/messages/{zh-CN,en-US}.json` | +12 each | add keys |

Every overlap is additive (one model class, one router registration, disjoint
i18n keys, disjoint type blocks), so merge conflicts resolve by keeping both
sides. The version files and the Alembic chain are the only true
single-writer resources.

## Confirmed facts (read-only survey, 2026-10-16)

- `PurchaseRequisition.delivery_address` and `PurchaseOrder.delivery_address`
  are single `Text` columns (`models/__init__.py:433`, `:543`), added by
  migration `0055`.
- The field is a bare `<Input>` in `PRNew.tsx:392` and `PREdit.tsx:350`;
  displayed at `PRDetail.tsx:291` and `POInfoCard.tsx:40`.
- **No address book model exists** among the 72 model classes. "Pick an
  existing address" has no data source today; the table is the first piece,
  not the dropdown.
- PR → PO propagation happens at three sites in `services/purchase.py`
  (`:826`, `:973`, `:1537`), all `delivery_address=pr.delivery_address`.
- `POOut` has no generic update endpoint; PO addresses are inherited only.
- `update_pr` gates every field on `if payload.x is not None`, so **an explicit
  `null` cannot clear a field**. The frontend sends
  `values.delivery_address?.trim() || null`, which means clearing the address
  on edit silently fails today. Pre-existing defect, in scope to repair for the
  delivery fields via `payload.model_fields_set`.
- Reusable precedents: `ItemPickerWithCreate.tsx` (pick-or-create),
  `MarqueeOption.tsx` (long-label handling), `components/ui/Mono.tsx`.
- `PRNew` autosaves `form.getFieldsValue()` plus `items`; new fields must be
  ordinary `Form.Item`s to be captured.
- Design constraints: `docs/DESIGN.md` §4.3 allows only 8 font sizes (12 / 13 /
  14 / 14w500 / 16 / 18 / 24 / 30); §7.7 defines Select styling; tokens only, no
  hardcoded hex.

## Write scope

Backend, new: `app/models` (DeliveryAddress), `app/schemas` (address book
in/out/update), `app/services/delivery_addresses.py`,
`app/api/v1/delivery_addresses.py`,
`migrations/versions/0060_delivery_address_book.py`,
`tests/unit/test_delivery_addresses.py`.

Backend, edited: `app/models/__init__.py`, `app/schemas/__init__.py`,
`app/services/purchase.py`, `app/api/__init__.py`,
`app/i18n/messages/{zh-CN,en-US}.json`, `tests/unit/test_purchase.py`.

Frontend, new: `components/DeliveryAddress/` (`index.ts`,
`DeliveryAddressSelect.tsx`, `DeliveryAddressModal.tsx`,
`DeliveryAddressSelect.test.tsx`).

Frontend, edited: `api/index.ts`, `pages/PurchaseRequisitions/PRNew.tsx`,
`pages/PurchaseRequisitions/PREdit.tsx`,
`pages/PurchaseRequisitions/PRDetail.tsx`, `components/PO/POInfoCard.tsx`,
`i18n/locales/{zh-CN,en-US}/common.json`.

Release files: the four version locations plus `CHANGELOG.md`.

No new `resource_type` in the business activity-log whitelist; the address book
is auxiliary data, so it stays out of `resource_activity_logs`.

## Design decisions

- **Ownership is hybrid.** `owner_id IS NULL` is a company-wide shared entry
  maintained by admins / procurement managers; a non-null `owner_id` is a
  private entry. Visibility is
  `owner_id IS NULL OR owner_id = :me`, both scoped to the reader's company.
- **Requisitions store a snapshot, never a reference.** `delivery_address_id`
  is provenance only (`ON DELETE SET NULL`); editing or deleting an address
  book entry must never rewrite a historical requisition.
- **`delivery_address` keeps its name.** Its meaning narrows to "detailed
  address". Renaming would force a data migration, touch all three PO
  propagation sites, and break export columns for no functional gain.
- **Ordering is by `usage_count` then `last_used_at`**, so frequently used
  addresses float to the top. Incremented when a PR saves with an
  `delivery_address_id`.
- **Option rendering uses a three-tier type scale**, not `MarqueeOption`:
  - contact name — 14px / 500 (`body-em`)
  - phone — 12px (`caption`) in mono, right-aligned
  - detail — 12px (`caption`) tertiary, `-webkit-line-clamp: 2`, `title` for
    the full text

  `MarqueeOption` scrolls a single line on hover; addresses are structured
  multi-line text and scrolling actively hurts scanning a dropdown.
- **Dropdown is wider than its trigger**: `popupMatchSelectWidth={false}` with
  `dropdownStyle={{ minWidth: 420 }}`.
- **Phone is length-limited to 32 and never format-validated.** Extensions and
  overseas numbers must survive; consistent with the project rule that a
  blocking flow is worse than an admin backstop.
- **Selecting fills *copies* of the three fields**, so a picked address stays
  editable (e.g. change the suite number) instead of becoming read-only.

## Frontend wiring hazards

1. The Select `value` binds to `delivery_address_id` only; the three text
   fields are filled via `form.setFieldsValue` in the pick handler.
2. Editing any of the three text inputs clears `delivery_address_id` to mark
   the value as hand-typed. Do this in each `Input`'s own `onChange`, **not** in
   `Form.onValuesChange` — `setFieldsValue` also fires `onValuesChange`, so the
   programmatic fill would immediately clear the id it just set. A ref guard
   works but is avoidable.
3. All three new fields plus the id need `Form.Item` wrappers so the existing
   `useAutosave` captures them.
4. All hooks must precede any early return (`AGENTS.md` §5.17).
5. i18n keys need zh-CN and en-US in the same commit (§5.18).

## Acceptance criteria

- `ruff check app`, `ruff format --check app` pass.
- `npm run type-check`, `npm run build` pass.
- Backend unit tests cover: shared-plus-own visibility, a plain user cannot
  create a shared entry, cannot edit another user's entry, `usage_count`
  ordering, PR save bumping `usage_count`, and PR → PO propagation of all three
  fields.
- Frontend component test covers the three-tier option rendering and the pick
  handler filling three fields.
- Legacy rows with only `delivery_address` still render on `PRDetail` and
  `POInfoCard` without a crash or an empty "—" for the whole block.
- Clearing all three fields on edit actually persists the clear.
- Browser E2E on an isolated database before this is called delivered.

## Verification (actual, 2026-10-16)

All green on `07e315e` (the merge commit), i.e. against current `main`.

| Check | Result |
|---|---|
| `ruff check app` | pass |
| `ruff format --check app` | 99 files already formatted |
| Backend `pytest tests/` | 848 passed, 12 skipped, 1 xfailed, 1 xpassed |
| Migration chain | 60 revisions, exactly one head `0060` |
| Migration round trip | `upgrade → downgrade → upgrade` on `mica_test`; table, indexes, FK names verified via `information_schema` |
| Frontend `tsc --noEmit` | pass |
| Frontend `npm run build` | pass (4.35s) |
| Frontend `vitest run` | 82 passed / 15 files |
| i18n parity | backend and frontend, zero diff both directions |

Re-run in full after merging `main`; the merge touched only version files and
`CHANGELOG.md`, but the numbers above are the post-merge ones.

### Browser E2E (independent stack, 2026-10-16)

Ran against an isolated stack — its own database (`mica_e2e_addr`, since
dropped), uvicorn on 8013 and Vite on 5179 — so the shared 8900 stack was never
touched. Script kept at `/tmp/e2e-address.cjs`; screenshots at `/tmp/e2e-*.png`.

Flow exercised: log in → open the new-PR form → open the address book (empty
state) → create an entry from inside the dropdown → verify the copy-back →
reopen the dropdown → type by hand and confirm the entry detaches.

Measured on the live DOM, not asserted from source:

| Observation | Result |
|---|---|
| Option rows rendered | 3 |
| Contact name computed style | `14px`, weight `500` |
| Phone computed style | `12px` (mono) |
| Detail `-webkit-line-clamp` | `2` |
| Long address text in full | preserved (no single-line truncation) |
| Copy-back into the three fields | name / phone / detail all correct |
| `delivery_address_id` after creation | set (selector showed the new entry) |
| Manual edit of a field | entry detached (`delivery_address_id` cleared) |

**Three real defects this run found, all now fixed in `fd9a852`:**

1. `DeliveryAddressSelect` dropped the `id` injected by `Form.Item`, so the
   address-book label pointed at nothing.
2. `dropdownStyle` / `dropdownRender` are deprecated in antd 5.29 and logged a
   warning on every form render.
3. The create modal's `useForm` was never connected while the modal was closed.

Two antd warnings still appear on that page and are **not** from this
workstream: `ItemPickerWithCreate.tsx` uses `Form.useForm()` with a modal that
has no `forceRender`, plus a deprecated `dropdownRender`. Left alone as
out-of-scope — worth a separate fix.

## Release notes (for the `chore(release)` commit)

Draft for `CHANGELOG.md`. It is deliberately **not** on this branch: since
v1.56.2 the changelog and the four version files ship in one release commit.

```markdown
### 新增（收货地址改为地址簿下拉，并拆成收件人 / 电话 / 详细地址三个字段）

采购申请与采购订单的收货信息原本是单个自由文本框，写法因人而异、无法复用。现在改为「地址簿 + 三个结构化字段」：创建或编辑申请时可以从下拉里挑一个存过的地址，也可以直接手输。

- **地址簿表 `delivery_addresses`**：`owner_id IS NULL` 是公司共享条目（管理员与采购经理维护），非空则是个人私有条目，两者都按读自己公司过滤。列表按 `usage_count` → `last_used_at DESC NULLS LAST` 排序，常用地址自动浮到前面（不用 `NULLS LAST` 的话，Postgres 的 `DESC` 会把从没用过的排在前面）
- **PR / PO 各加三列**：`delivery_contact_name`、`delivery_contact_phone`、`delivery_address_id`。原有 `delivery_address` **不改名、不迁移数据**，语义收窄为「详细地址」——因此历史单据、导出列与三处 PR→PO 透传逻辑全部保持不动
- **申请单存快照，不存引用**：三个文本字段在保存时复制，`delivery_address_id` 只是溯源信息且 `ON DELETE SET NULL`。修改或删除地址簿条目**不会**改写任何历史单据，有专门的回归测试守着这条不变量
- **下拉是三行式自定义样式**：收件人 14px/500、电话 12px 等宽、详细地址 12px 三级色且最多折两行并带 `title` 全文——长地址不再被压成一行省略号（浏览器实测 computed style 已验证）。下拉面板固定 420px 与触发框宽度解耦。地址是结构化文本，故没有沿用单行滚动的 `MarqueeOption`
- **选中的地址仍可微调**：挑一个条目后三个字段是副本，用户可继续改门牌号；手动改动任一字段会把 `delivery_address_id` 置空，标记为「自定义」
- **修复既有缺陷**：`update_pr` 原先对每个字段都用 `if payload.x is not None`，导致表单清空地址后传的 `null` 被静默忽略、刷新后又冒出来。收货相关四个字段改用 `model_fields_set` 判断，现在能真正清空
- **权限**：任何人都能读自己可见的条目并维护自己的私有条目；共享条目只有 `admin` / `procurement_mgr` 能增删改。别人的私有条目返回 404 而非 403，避免确认 id 是否存在
- **顺带**：`field.delivery_address` 文案由「收货地址」改为「详细地址」；电话号码只限长度不校验格式（分机号、境外号都必须能存）

### 验证

- 新增 26 个用例：地址簿服务层（共享/私有可见性、权限边界、排序、`model_fields_set` 清空语义、删除后快照不变、保存申请单时 usage 自增）、真实 HTTP 层（完整增删改查往返、403 / 404 / 401、`/api/v2` 镜像）、PR→PO 三字段透传、前端组件（三行式渲染、选择回填、共享标记、空态、清空回传 `null`、无 antd 弃用警告）
- 迁移 0060 在测试库实跑 `upgrade → downgrade → upgrade` 往返，表结构、索引与命名约束逐项核对通过
- 浏览器 E2E 在独立栈（独立库 + 8013/5179）跑通完整流程：登录 → 新建申请 → 打开地址簿空态 → 下拉内新建地址 → 三个字段回填 → 重开下拉 → 手改字段解除绑定。实测 computed style 确认三行式字号与两行截断
- 后端全量 `pytest`：852 passed / 12 skipped / 1 xfailed / 1 xpassed；`ruff check app` 与 `ruff format --check app` 通过
- 前端 `npm run type-check`、`npm run build`、`vitest run`（93 passed）通过
```

New coverage, 25 cases: address book service (shared/private visibility,
403 vs 404 boundaries, `NULLS LAST` ordering, `model_fields_set` clear
semantics, snapshot survives entry deletion, usage bump on requisition save),
real HTTP surface (full CRUD round trip, 403/404/401, `/api/v2` mirror),
PR → PO propagation of all three fields, plus the four delivery fields.

`added` but not done:

- **Browser E2E was not run.** It needs a live stack; the API surface is covered
  by real-HTTP tests instead. Running it means starting the backend and Vite on
  isolated ports (not 8900/8012/5178) and seeding a database, which should be a
  deliberate, separately authorised step on a shared machine.
- **Field-level permission on the phone number** is still undecided; see below.

## Merge and release ordering

Commit and release **serially**, never concurrently with the PAT workstream.
`PROJECT_STATE.md` already records the last collision: *"Deployment encountered
concurrent container replacement; publisher stopped competing mutations."*
The §9 release flow (four version files → `gh release` → ssh deploy) is a
global single-writer operation.

Merge order: PAT `1.56.0` first (it holds the lower version and migration
`0059`), then rebase this branch so the migration links
`0059 → 0060` and the version becomes `1.57.0`.

## Open decision (not yet confirmed by the user)

Contact phone numbers are personal data (`phone` in the frontend i18n audit).
Field-level read permission via Cerbos (`deploy/cerbos-policies/`, per
`AGENTS.md` §5.13) was proposed but not accepted. Until decided, the phone
field follows the requisition's ordinary visibility.
