# QuoteFlow functional QA evidence - 2026-10-06

This directory preserves the functional checkpoint evidence before the calibrated visual redesign. The screenshots show an interim interface, not final portfolio artwork. All data is local synthetic demo data. CONNECTED entry and offline health are explicit browser fixtures, not evidence of a live provider or customer account.

The 20 evidence files were copied from `tmp/customization-qa` with SHA-256 equality checks. Originals remain unchanged in that directory. Source changes, executed checks, and remaining limits are recorded in the [local improvements report](../../LOCAL_IMPROVEMENTS_2026-10-06.md).

## Browser evidence

[Result JSON](result.json): passed, 11 screenshots, zero page errors.

| Evidence | Case |
| --- | --- |
| [01-studio-settings-desktop.png](01-studio-settings-desktop.png) | Persisted studio defaults on desktop |
| [02-studio-settings-mobile.png](02-studio-settings-mobile.png) | Settings at mobile width |
| [03-invalid-template-mobile.png](03-invalid-template-mobile.png) | Invalid import produces a visible error |
| [04-custom-catalog-desktop.png](04-custom-catalog-desktop.png) | Custom catalog categories |
| [05-proposal-list-desktop.png](05-proposal-list-desktop.png) | Separated proposal list items on desktop |
| [06-proposal-list-mobile.png](06-proposal-list-mobile.png) | Separated list items at 390 px |
| [07-price-error-mobile.png](07-price-error-mobile.png) | Server pricing error feedback |
| [08-accepted-customer-mobile.png](08-accepted-customer-mobile.png) | Accepted customer review |
| [09-viewer-settings-desktop.png](09-viewer-settings-desktop.png) | Viewer settings are read-only |
| [10-connected-auth-desktop.png](10-connected-auth-desktop.png) | Mocked CONNECTED password entry |
| [11-offline-entry-mobile.png](11-offline-entry-mobile.png) | Offline health fixture |

## PDF evidence

The downloaded [customized EUR/VAT proposal](customized-proposal.pdf) has two pages. Its final-renderer Poppler renders are [page 1](customized-page-1.png) and [page 2](customized-page-2.png).

The [long-content stress proposal](long-content-stress.pdf) exercises long names, long scope, and 120 assumption lines over four pages. Its final-renderer Poppler renders are [page 1](stress-page-1.png), [page 2](stress-page-2.png), [page 3](stress-page-3.png), and [page 4](stress-page-4.png).

Text assertions and visual inspection passed for these Latin-content fixtures. Non-Latin fonts, live-model quality, and PostgreSQL concurrency remain unverified.
