# Whole-app layout: full-width list pages

## Objective

Every page's main content was capped at `maxWidth: 1440`. On a 2864px display
that wasted ~600px on each side **while the tables inside were being squeezed
hard enough to wrap their own cells** — `zh-CN` broke across two lines, and so
did every timestamp. Goal: make list pages use the width available, keep forms
readable, tighten the density.

## The audit (why this was measured, not eyeballed)

Static grepping was misleading. `title:` also matches `Card`/`Modal` titles, so
a naive sweep reported `ContractDetail` at 27 columns and `SupplierPortal` at
26 — both wrong. A whole-app browser run was used instead: 34 static routes (plus
the detail pages that had seed data) at 2864×1464, measuring per page:

- content width vs. available width (utilisation)
- every table cell height, against the single-line baseline
- whether a table overflows without a scroll container

Script kept at `/tmp/audit-pages.cjs`.

## Changes

| File | Change |
|---|---|
| `components/Layout/AppLayout.tsx` | `maxWidth: 1440` → `undefined` for list/detail pages, kept for form pages; page padding 24px → 16px |
| `pages/admin/UsersPanel.tsx` | added the missing `scroll={{ x: 'max-content' }}`, explicit column widths, `MonoNum` for the timestamp |
| `pages/Items.tsx` | uom 60 → 100px; width added to code/name/category |
| `pages/admin/RoutingsPanel.tsx` | width added to feature/model/temperature/tokens |
| `pages/admin/DocumentTemplatesPanel.tsx` | width added to name/file/filename-template |
| `pages/SearchResults.tsx` | dropped its own 1200px cap and 24px padding |
| `pages/NotificationCenter.tsx` | dropped duplicated 24px padding (cap kept on purpose) |

**Form pages** are matched by `FORM_PAGE_PATTERNS` in `AppLayout`, so the rule
lives in one place rather than being scattered per page: a form is one narrow
column of fields, and stretching a single input across 2600px makes it harder to
fill in. Matched: `/purchase-requisitions/new`, `/new/:copyId`, `/:id/edit`,
`/rfqs/new`, `/rfqs/:id/edit`.

## The interesting bug

`Items` looked "ragged" and the audit flagged three cells at h=59. The obvious
suspect was the long `specification` text. It was not: the **`uom` column was
60px and could not fit `LICENSE`**, so it rendered as `LICEN` / `SE` and pushed
the whole row taller. Widening it to 100px fixed all three.

Worth recording because reading the code suggested the wrong column.

## Verified

| Check | Before | After |
|---|---|---|
| List/detail content width | 1440 | **2644** |
| Form page content width | 1440 | 1440 (by design) |
| Page padding | 24px | **16px** |
| `/items` wrapped cells | 3 | **0** |
| `/items/:id`, `/suppliers/:id` | — | 2644px, 0 wrapped |

Remaining "wrapped" hits in the audit are two benign cases, both checked by
hand: AntD's empty-state cell (it fills the row height) and the deliberate
two-line name/code cell in document templates. `ai-routing`'s h=57 is a
`<Select>`, whose natural height is ~57px.

Frontend `type-check`, `build` and `vitest` (93 passed) all green.

## Deliberately not changed

- **`NotificationCenter` keeps its 1000px cap.** It is a single-column reading
  list; full-width text at 2.8K is harder to scan, not easier.
- **`SupplierPortal` was left alone.** Its route `/portal/:token` renders
  *outside* `AppLayout`, so it supplies its own padding legitimately.

## Released

**v1.58.0** — merged as `d38e616`, release commit `32159fb`, deployed with
`upgrade.sh --tag v1.58.0` (168s). Production reports `1.58.0`, `db: true`,
`cerbos: true`; `.env`, image tags and container references all read `1.58.0`,
which also confirms the one-release-late `APP_VERSION` bug from v1.57.2/1.57.3
is gone.
