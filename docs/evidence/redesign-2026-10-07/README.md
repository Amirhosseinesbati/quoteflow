# QuoteFlow redesign verification — 2026-10-07

These screenshots and PDF renders preserve the approved proposal workbench with local synthetic data. The [workbench report](../../WORKBENCH_2026-10-07.md) explains implementation, scope, and limitations; [client setup](../../CLIENT_SETUP.md) explains configuration.

## Executed final checks

| Check | Result |
| --- | --- |
| Backend Ruff | Passed, `ruff check src tests/backend --no-cache` |
| Full backend Mypy | No issues in 20 source files |
| Backend regression suite | 49 passed in 11.25 s |
| Frontend ESLint | Passed on final source |
| Frontend TypeScript | Passed on final source |
| Frontend Vite build | 1,945 modules, 986 ms; CSS 39.87 kB / JS 365.22 kB |
| Complete real browser journey | Passed separately in Dark and Light, from UI intake through separate unauthenticated clarifications, edit/diff/approval/PDF/publication/acceptance |
| API contract | 31 route methods and six request shapes passed |
| Customization/auth regression | [Result](customization-result.json): passed, 11 screenshots, zero page errors; settings/import/export/catalog/history/expiry/logout/viewer/repeated acceptance covered |
| Final theme/workbench QA | [Result](result.json): passed, 27 screenshots, zero page errors; 448 sampled text contrasts, lowest ratio 5.54:1 |

The [theme suite result](result.json) includes preferences, storage failure, prepaint/CSP bootstrap, System OS changes, intact drafts/pricing/approval state, no writes from theme changes, document invariants, native dialog/keyboard behavior, mobile control heights, overflow, reduced motion, errors, and sampled contrast. The sample is not an accessibility certification. Offline and CONNECTED entry cases in the customization suite are explicit browser fixtures.

## Representative screens

| Screen | Dark | Light |
| --- | --- | --- |
| Desktop workbench | [Dark](05-workbench-dark-viewport.png) | [Light](05-workbench-light-viewport.png) |
| Mobile package comparison | [Dark](06-workbench-mobile-dark-viewport.png) | [Light](06-workbench-mobile-light-viewport.png) |
| Intake | [Dark](03-intake-dark.png) | [Light](04-intake-light.png) |
| Scope/pricing editor | [Dark](07-editor-dark.png) | [Light](07-editor-light.png) |
| Mobile price error | [Dark](08-price-error-mobile-dark.png) | [Light](08-price-error-mobile-light.png) |
| Customer review | [Dark](10-customer-mobile-dark.png) | [Light](10-customer-mobile-light.png) |
| Settings | [Dark](12-settings-dark.png) | [Light](12-settings-light.png) |
| Catalog | [Dark](13-catalog-dark.png) | [Light](13-catalog-light.png) |

[Keyboard/focus approval dialog](09-approval-dialog-dark.png) · [accepted customer](11-customer-accepted-light.png) · [server error](15-server-error-light.png)

The published PDF downloaded under [Dark](proposal-dark.pdf) and [Light](proposal-light.pdf) is byte-identical for the same version. The document remains deliberately light and printable. Both rendered [page 1](proposal-page-1.png) and [page 2](proposal-page-2.png) were visually inspected; [PDF assertions](pdf-result.json) record the page count and file hash. Poppler reported nonfatal Symbol/ArialUnicode display-font warnings, but tested Latin content showed no clipping or overlap. Non-Latin font coverage remains unverified.

[Dark customer clarification](journey-dark-clarification.png) · [Light customer clarification](journey-light-clarification.png) · [Dark acceptance](journey-dark-accepted-mobile.png) · [Light acceptance](journey-light-accepted-mobile.png) · [Viewer settings](auth-viewer-settings-dark.png) · [Mocked CONNECTED entry](auth-connected-entry-dark.png) · [Offline fixture](auth-offline-entry-mobile-dark.png)

The [copy manifest](manifest.json) records SHA-256 equality with retained originals.

Originals remain under `tmp/theme-qa`. Complete journey captures remain under `tmp/browser-check-dark` and `tmp/browser-check-light`; the 2026-10-06 evidence is retained separately. No live provider, deployment, public export, commit or push was performed by this worker.
