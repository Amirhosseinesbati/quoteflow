# QuoteFlow functional checkpoint - 2026-10-06

This pass changes only QuoteFlow. The existing dirty README, gitignore, DEPENDENCIES/EVALUATION/OPERATIONS/PRODUCT documents and `teaser_assets` were preserved. No sibling project, shared parent script, deployment, paid provider, secret, push, or publish was used. This dated pass captured the interim functional appearance. The subsequent approved design and Light/Dark/System rollout are recorded in the [2026-10-07 workbench report](WORKBENCH_2026-10-07.md).

## Implemented

- Workspace-persisted, admin-only studio settings: name/accent, six supported currencies, tax label/rate, contingency, discount approval threshold, title/summary/terms/footer templates. Strict validation and optimistic revision checks prevent silent stale saves. A migration adds `workspace_preferences` without modifying existing workspace/quote data.
- Portable studio-default JSON import/export with draft review, bounded file size, and server-side validation. It contains no client data or secrets. Catalog rows are managed separately.
- Frozen document identity inside each proposal's existing content hash. Old versions retain branding/currency when settings change; revisions retain their source document identity; fresh options adopt new defaults. Accepted quotes remain immutable.
- Historical catalog lookup scoped to the authenticated workspace; editing a quote loads the correct service IDs/rates. Corrected the frontend's object-versus-number catalog version mismatch. Custom categories appear in filters and service editing.
- Separated proposal list items and numbered milestones/next steps in browser and PDF, displayed terms, explicit currency/tax label/percentage, and paragraph-level pagination for long PDF sections. Repeated table headers, row continuation, and grouped totals remain supported.
- Existing-session restoration, server-side sign out, workspace query-cache clearing, expired-session entry, read-only viewer controls, and a password entry screen when the API reports CONNECTED. Removed automatic privileged demo re-login from a stored role preference.
- Native modal dialogs with focus containment, Escape, and focus restoration. Unsaved quote changes block sharing/approval and prompt before switching versions. Pricing previews clear after edits. PDF links are enabled after publication. Clipboard failures produce an actionable message.
- Missing-record guards in existing API/workflow operations and corrected seed/provider/context-manager types. No graph routing or live-provider behavior was changed.
- A local SQLite preview script and [client configuration guide](CLIENT_SETUP.md).

## Executed verification

All checks used installed dependencies and ran sequentially. Only local synthetic data and isolated headless Edge were used. Frontend dependencies had stale absolute junctions from the project's previous folder name; 348 junctions were rebased strictly inside this project's `node_modules`, without downloads or global changes. The moved Python environment is handled by an explicit source path in the preview script.

| Check | Command / observed result |
| --- | --- |
| Backend lint | From `apps/api`: `.venv/Scripts/python.exe -m ruff check src tests/backend --no-cache`; passed |
| Backend types | `.venv/Scripts/python.exe -m mypy src/quoteflow --ignore-missing-imports --cache-dir ../../tmp/mypy-customization`; **no issues in 20 source files** |
| Backend suite | `.venv/Scripts/python.exe -m pytest tests/backend -q -p no:cacheprovider --basetemp=../../tmp/pytest-client-header-final`; **49 passed in 11.75 s** |
| Frontend lint | From `apps/web`: `node node_modules/eslint/bin/eslint.js src`; passed |
| Frontend types | `node node_modules/typescript/bin/tsc --noEmit`; passed |
| Frontend build | `node node_modules/vite/bin/vite.js build`; **1,943 modules, 889 ms**, exit 0 |
| API/client contract | `QUOTEFLOW_OPENAPI_URL=http://127.0.0.1:8316/openapi.json`, `node scripts/check-openapi.mjs`; **31 route methods and six request payload shapes** passed |
| Full browser workflow | `QUOTEFLOW_URL=http://127.0.0.1:4316/`, `QUOTEFLOW_BROWSER=msedge`, `node scripts/browser-check.mjs`; passed twice, including after API restart on the final source |
| Customization/error browser checks | `node scripts/customization-check.mjs` on the same preview; passed twice after correcting focus restoration; **11 screenshots, zero page errors**, [saved result](evidence/upgrade-2026-10-06/result.json) |
| Migration | Single Alembic head `d62af884a315`; migration regression preserved existing workspace rows; fresh local preview migrated through all revisions and restarted successfully |
| API health | `http://127.0.0.1:8316/api/health`: `status=ok`, `mode=DEMO`, `synthetic=true` |
| PDF inspection | Downloaded customized EUR/VAT two-page PDF and generated the long-scope/120-line four-page regression fixture; pypdf assertions passed and Poppler PNGs were visually inspected with no clipping/overlap in these fixtures |

The first full Mypy run exposed 80 errors, including existing nullable-record and seed type issues. After the scoped fixes, the complete source check passed; this is a real static check, not a reduced file subset. The initial native-dialog browser test caught focus restoration after Escape; the corrected implementation passed repeated checks. Poppler emitted nonfatal missing Symbol/ArialUnicode display-font messages; tested Latin content rendered visibly. Non-Latin PDF support remains unverified.

`git diff --check` still reports line-ending/blank-line warnings in the preexisting dirty `.gitignore`, README and OPERATIONS document; they were left intact. Check only the implementation paths when reviewing this pass. Python temp/cache operations and headless browser spawning required the host's approved local execution path; no download or external service was needed.

## Browser cases and evidence

The workflow journey exercises actual UI intake, requirement evidence, a separate unauthenticated customer's clarification answers, three options, changed line quantity, scope diff, internal approval, PDF/link generation, and customer acceptance. It was repeated with persisted Northstar/EUR/VAT defaults after restarting the latest-source API.

The additional suite verifies persisted settings after reload, valid/invalid template import/export, custom catalog categories, native dialog focus/Escape/return, visible list markers and separated list item geometry, no page-wide overflow at desktop/390 px, unsaved-change sharing guards, server pricing errors, stale preview invalidation, PDF download, replaced review-token 410, repeat acceptance returning the same handoff, logout-cookie replay 401, viewer settings disabled, and session-expiry handling. CONNECTED entry and offline health are explicit browser fixtures; they do not establish a working live customer account or provider connection.

The [durable evidence index](evidence/upgrade-2026-10-06/README.md) contains all 11 customization/error screenshots, the browser result, and both PDFs with their six rendered pages. These are functional QA evidence of the interim appearance, not final portfolio artwork. All 20 copied files were verified against the originals with SHA-256; the originals remain in `tmp/customization-qa`.

- [Proposal desktop](evidence/upgrade-2026-10-06/05-proposal-list-desktop.png) and [390 px mobile](evidence/upgrade-2026-10-06/06-proposal-list-mobile.png)
- [Studio settings](evidence/upgrade-2026-10-06/01-studio-settings-desktop.png)
- [Price error](evidence/upgrade-2026-10-06/07-price-error-mobile.png) and [accepted customer view](evidence/upgrade-2026-10-06/08-accepted-customer-mobile.png)
- [Mocked CONNECTED entry](evidence/upgrade-2026-10-06/10-connected-auth-desktop.png) and [offline entry](evidence/upgrade-2026-10-06/11-offline-entry-mobile.png)
- [Customized EUR/VAT PDF](evidence/upgrade-2026-10-06/customized-proposal.pdf), rendered [page 1](evidence/upgrade-2026-10-06/customized-page-1.png) and [page 2](evidence/upgrade-2026-10-06/customized-page-2.png)
- [Long-content stress PDF](evidence/upgrade-2026-10-06/long-content-stress.pdf), rendered [page 1](evidence/upgrade-2026-10-06/stress-page-1.png), [page 2](evidence/upgrade-2026-10-06/stress-page-2.png), [page 3](evidence/upgrade-2026-10-06/stress-page-3.png), and [page 4](evidence/upgrade-2026-10-06/stress-page-4.png)
- `tmp/browser-check/` retains the full journey captures locally.

## Preview and remaining work

From the project root, run `.\scripts\preview-local.ps1`; web/API ports are **4316/8316**. Its data/assets/logs stay under ignored `tmp/client-preview`. The preview was running and healthy at the end of verification. It uses SQLite and no live calls; it is not a verified PostgreSQL/Docker deployment.

The visual redesign was subsequently completed in the [2026-10-07 workbench rollout](WORKBENCH_2026-10-07.md). Still open: PostgreSQL concurrent settings saves and quote transitions, Docker redeployment, connected-provider behavior, customer account provisioning/SSO/MFA, multilingual PDF fonts, coordinated backup/restore, bulk catalog import, richer quote/template matching rules, and real human review of proposal quality. Currency changes label catalog amounts without exchange conversion. Synthetic tests do not measure live-model semantic quality, customer accuracy, or production security.
