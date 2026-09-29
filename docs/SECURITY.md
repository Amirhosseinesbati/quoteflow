# Security model

This document defines pilot security requirements and review points. A checked box or general design statement is not evidence that a control is implemented; actual test status is in [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md).

## Trust boundaries

The staff browser, public/demo form, portal customer, uploaded brief/PDF, model output, HubSpot response and any future fetched URL are untrusted inputs. The API is the authorization and pricing boundary. SQL/database records, graph checkpoints, files, caches, trace events and exports all need the same workspace scope. A LangGraph thread ID, quote ID or asset path is never a bearer permission. CONNECTED credentials must remain server-side and out of OpenAPI examples, frontend bundles, logs and exports.

## Identity and roles

Use maintained password hashing/session libraries, server-issued sessions and admin/operator/viewer roles. Deploy cookies with `HttpOnly`, `Secure`, an appropriate `SameSite` policy and short session lifetime; protect state-changing cookie requests against CSRF. Demo accounts live in a separate demo namespace and cannot bypass authorization in a customer workspace. Test cross-workspace reads, writes, SSE streams, file downloads, approvals and graph resume, not merely list filters. A portal token is a separate purpose-bound capability, limited to one client, one proposal version/action and expiry.

## Approval and acceptance

Approval binds quote version, catalog version, normalized scope/price fields and content hash. At execution, recheck role, authorization, current quote state and hash. A changed version revokes or invalidates prior approval and review links. Customer acceptance records an acknowledgement of the version shown, not a legal e-signature. A token must be securely random, stored as a hash, checked in constant time where applicable, scoped to action/version/client, expire, and fail closed when replaced or modified. A single transactional unique handoff claim handles repeated acceptance; external delivery uses outbox keys and reconciliation. Arbitrary third-party writes cannot be promised exactly once.

Local SQLite integration tests in `test_review_guards.py` verified that a customer portal answer cannot target another brief's question, creates a persisted brief revision and supersedes/regenerates quote options. The same file verified 410 on acceptance through expired, replaced and superseded-version links, and 409 when price or scope edits try to publish using an earlier approval. These are four targeted guard cases; other token actions, concurrency and the same guard matrix against PostgreSQL remain to be tested. A separate live PostgreSQL workflow did complete through customer acceptance after API restart, with one matching handoff.

## Content, uploads and rendering

- Validate file type by content and configured allowlist, enforce size/page limits, scan/parse with timeouts and store by generated scoped ID outside web static roots. Reject active or malformed content safely.
- Treat briefs, PDFs, customer answers, retrieved text and tool responses as data, never as authority to alter system rules, catalog rates, destinations or approval policy. Validate structured model output against schemas and cross-check evidence spans.
- Sanitize rendered Markdown/HTML. Escape text in proposal/PDF templates. Neutralize spreadsheet formula prefixes in CSV exports, including cells beginning with `=`, `+`, `-`, `@`, tab or carriage return where relevant.
- For any user-provided URL fetching, allowlist destinations and block loopback, private, link-local and cloud metadata ranges, including redirect hops. Prefer no arbitrary remote fetching in v1.

## Data and logging

Use parameterized SQL and least-privilege DB users. Scope assets and checkpoint access by workspace. Encrypt traffic in customer deployments and encrypt backups at rest. Set retention and redaction for raw briefs, attachments, PDFs, model traces, audit events and backups. Structured business-event logs should include correlation ID, workspace ID and event class while omitting full brief text, credentials and portal tokens. Tracing is optional and disabled or redacted by default. A deletion/export request needs to include related files, checkpoints and logs according to the configured policy.

**Portal URL logging audit:** During local DEMO review, default Uvicorn and reverse-proxy access logs were found to record token-bearing portal paths. The container Uvicorn command now disables access logging with `--no-access-log`, and the Compose nginx configuration sets `access_log off;` plus `Referrer-Policy: no-referrer` to limit token-bearing URL disclosure through request referrers. A defense-in-depth filter on `uvicorn.access` redacts `/api/portal/<token>` in both parameterized and preformatted records. `apps/api/tests/backend/test_access_log.py` passed in the 22-test backend suite, checking redaction and idempotent filter installation. A boolean check of API/web container logs in the tested Compose run found no `/portal/` path; this sample does not cover all future traffic or upstream logging. Four disposable synthetic SQLite test databases that held earlier local tokens were removed, so those database-backed links are no longer active. Application-level safe business events remain available without token values. Removing those databases does not erase earlier local log output or cover a customer's external load balancer, CDN, WAF, APM or tracing configuration. Inspect and redact such upstream logs before a connected deployment, avoid sharing token-bearing URLs, and rotate/revoke any exposed live tokens. No token values are reproduced here.

## External adapters

Local CRM/outbox adapters are demo simulations with the same application-facing contract as connected adapters. HubSpot credentials and model keys come from server configuration. Restrict HubSpot scopes to contact/deal needs, use bounded timeouts and rate-limit handling, and log safe provider event IDs for reconciliation. Missing credentials or failed requests must remain explicit. An ambiguous remote timeout is an uncertain delivery state until reconciled.

## Required security evidence before pilot

| Check | Status |
| --- | --- |
| Cross-workspace staff/portal/asset/SSE access tests | Staff brief/quote isolation and cross-brief portal clarification 404 passed on SQLite; asset/SSE and full resource matrix pending |
| Stale, expired, tampered and replaced token tests | Tampered token 404 and expired/replaced/superseded-version acceptance 410 passed on SQLite; other actions and cross-client cases pending |
| Approval hash and accepted immutability tests | Price/scope edits changed hash and required fresh approval; both new and previously approved versions blocked from publish (409); accepted-version patch 409 passed on SQLite. Broader state/concurrency matrix pending |
| Upload type/size, XSS and CSV formula tests | One CSV leading-whitespace formula-escape unit case passed; upload and XSS checks and broader CSV input matrix pending |
| Retry, concurrent acceptance and outbox dedupe tests | Pending verification |
| Secret scan, dependency/license review and backup encryption | Pending verification |

These controls require a deployment review for the customer's hosting, identity provider, TLS termination, backup store and retention obligations. This document is not a certification or legal assessment.
