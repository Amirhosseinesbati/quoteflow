# QuoteFlow workbench and theme rollout — 2026-10-07

The approved tool-focused design replaces the former studio layout with a compact proposal workbench. The brief stays beside the package comparison and the selected version. Investment, catalog scope, and version integrity are visible before the document. Scope language uses native expandable sections; line items, pricing policy, and the server-calculated preview share a bounded editor panel. Intake shows the real four-stage workflow and current workspace defaults instead of a decorative sample document.

The [completed functional pass](LOCAL_IMPROVEMENTS_2026-10-06.md) remains in place: workspace customization, catalog history, immutable document snapshots, approval boundaries, session restoration/logout, accessible native dialogs, separated proposal lists, and paginated PDF output. Backend behavior and PDF rendering code were not changed for this design rollout.

## Appearance contract

- Light, Dark, and System are available through a labeled native select on entry, the studio, and customer routes. The validated `quoteflow-theme` preference persists locally. Fresh/invalid preferences default to Dark, even on a light OS. A blocked storage API keeps the current choice usable in memory.
- System follows live OS changes; explicit Light/Dark ignore OS changes. Other tabs synchronize preference changes through the storage event. Appearance changes do not navigate, remount forms, recalculate pricing, or write to the API.
- A blocking same-origin `theme-init.js` and render-blocking `theme-base.css` apply the preference and canvas before the application bundle loads. No inline bootstrap script, eval, or inline bootstrap style is required. The bootstrap was checked independently under `script-src 'self'`; Vite's development refresh preamble is excluded from that fixture. This is not a whole-application production CSP audit.
- Semantic tokens cover canvas, navigation, surfaces, inputs, text, accent, success, warning, errors, focus, and borders. Native controls inherit the resolved color scheme. Keyboard tablists support arrows/Home/End; dialogs retain native focus containment/Escape/return. Reduced motion suppresses transitions, animation, and smooth scroll.
- The customer document uses a separate, fixed light palette and serif typography. Its geometry and contents stay equal across application themes. Exported PDF bytes stay identical for the same published version; no theme choice is sent to the PDF endpoint.

## Changed implementation paths

- `apps/web/index.html`, `public/theme-init.js`, `public/theme-base.css`: prepaint preference and canvas.
- `apps/web/src/lib/theme.tsx`, `lib/tabs.ts`, `main.tsx`: persisted appearance control/provider and keyboard tab traversal.
- `apps/web/src/App.tsx`, `features/IntakeForm.tsx`, `StudioPage.tsx`, `QuoteWorkspace.tsx`, `BriefWorkspace.tsx`, `PortalPage.tsx`: workbench layout, workflow context, editor grouping, theme access, stable navigation names, and keyboard/mobile interactions.
- `apps/web/src/workbench.css`, `document.css`, `styles.css`: semantic application themes and a separate stable document/print palette. Existing ancillary pages/components use semantic utility classes.
- `apps/web/scripts/browser-check.mjs`, `theme-check.mjs`: parameterized real customer workflow and appearance/state/error regression checks.

## Verification and evidence

Final check results and representative screenshots are indexed in [durable redesign evidence](evidence/redesign-2026-10-07/README.md). Its 44 evidence files were copied with SHA-256 equality checks; originals remain in `tmp`. The full browser journey covers actual UI intake, requirement evidence, a separate unauthenticated customer's answers, three options, line/discount edits, scope diff, internal approval, PDF/publication, and acceptance. It runs separately with `QUOTEFLOW_THEME=dark` and `QUOTEFLOW_THEME=light`.

The additional theme suite checks prepaint preferences, blocked storage, live System changes, persistence, intact intake/proposal/customer drafts, unchanged calculated prices and approval state, no API mutations on theme switches, desktop/390 px reflow, mobile control heights, native dialog/keyboard behavior, server pricing errors, unavailable API state, sampled text contrast, reduced motion, document geometry/palette, and identical PDF bytes. Its contrast sample is regression evidence, not a comprehensive accessibility certification.

From `apps/web`, with the local preview running:

```powershell
$env:QUOTEFLOW_URL='http://127.0.0.1:4316/'
$env:QUOTEFLOW_BROWSER='msedge'
node scripts/theme-check.mjs
$env:QUOTEFLOW_THEME='dark' # repeat with light
node scripts/browser-check.mjs
```

From the project root, `.\scripts\preview-local.ps1` starts the isolated synthetic SQLite preview on web/API **4316/8316**. Only installed dependencies are used. Live providers, Docker/PostgreSQL concurrency, customer provisioning/SSO/MFA, non-Latin PDF fonts, and real-model proposal quality remain outside verified scope. Currency defaults label catalog amounts without exchange conversion. Deployment and live integration validation are separate from this local workbench pass.
