# API contract

This is the target resource contract from the product brief. Endpoint paths, request bodies and OpenAPI generation must be reconciled with the running API; see [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) for what is verified. The server owns prices, quote versions, run IDs and authorization. All staff resources are scoped to the authenticated workspace and role. Portal operations use one purpose-bound review token and never accept workspace/client IDs as authority.

## Resource groups

| Resource | Required operations and behavior |
| --- | --- |
| `briefs` | Create from form, pasted text or validated text/PDF upload; list/read source and revision; run extraction; show evidence and uncertainty. |
| `clarifications` | Edit/operator approve questions; issue scoped response link; accept answer; create a new brief revision and trigger bounded regeneration. |
| `catalogs` | List immutable versions; validate/edit a draft catalog and price rules; publish a version; list 35 seeded demo services. |
| `quotes` and `quote versions` | Create quote, show three distinct scope options, edit proposal, compare versions, freeze accepted version and expose observable job progress. |
| `price previews` | Compute server-side Decimal totals from versioned catalog inputs and explicit quantity, discounts, contingency and tax policy; return line subtotals and rounding breakdown. Preview has no approval effect. |
| `approvals` | Request, approve/reject and read approval events. Approval must reference the exact version/hash and authenticated approver. |
| `assets` | Render/download approved PDF or safe CSV export with workspace checks and content metadata. |
| `portal responses` | Validate token, show only its proposal version, answer clarifications, accept/decline/request revision, and return a stable repeated-response result. |
| `handoffs` | Read one local handoff linked to the frozen accepted version; delivery state may be pending/retrying/uncertain. |
| `jobs` | Persist status/progress/failure/cancellation, expose authorized SSE progress and allow authorized cancellation where safe. |
| `connectors` | Surface local or HubSpot configuration and actual health without leaking secrets. |

## Current route inventory

The following paths were inspected in `apps/api/src/quoteflow/main.py` on 2026-09-28. Their presence in source is not a successful HTTP or authorization test; generated OpenAPI and a running API must still be checked.

| Area | Routes currently declared |
| --- | --- |
| Health/auth | `GET /api/health`; `POST /api/auth/demo`, `/api/auth/login`, `/api/auth/logout`; `GET /api/auth/me` |
| Brief intake | `GET, POST /api/briefs`; `POST /api/public/briefs`, `/api/briefs/upload`; `GET /api/briefs/{brief_id}`; `POST /api/briefs/{brief_id}/analyze` |
| Clarification | `GET, POST /api/briefs/{brief_id}/clarifications`; `PATCH /api/briefs/{brief_id}/clarifications/{clarification_id}`; `POST /api/briefs/{brief_id}/clarifications/{clarification_id}/answer`, `/api/briefs/{brief_id}/portal-link` |
| Quote/options | `POST /api/briefs/{brief_id}/options`; `GET /api/quotes/{quote_id}`, `/api/quotes/{quote_id}/diff`; `PATCH /api/quotes/{quote_id}/versions/{version_id}`; `POST /api/quotes/{quote_id}/versions/{version_id}/price-preview` |
| Approval/publish | `POST /api/quotes/{quote_id}/versions/{version_id}/submit-review`, `/api/quotes/{quote_id}/versions/{version_id}/publish`; `GET /api/approvals`; `POST /api/approvals/{approval_id}/decision` |
| Assets/export | `GET /api/quotes/{quote_id}/versions/{version_id}/pdf`, `/api/quotes/{quote_id}/versions/{version_id}/csv` |
| Customer portal | `GET /api/portal/{token}`; `POST /api/portal/{token}/clarifications/{clarification_id}` (and `/answer` alias); `POST /api/portal/{token}/response` |
| Handoff/outbox | `GET /api/handoffs`, `/api/outbox` |
| Catalog | `GET /api/catalog`, `/api/catalog/services`; `POST /api/catalog/services`; `PATCH /api/catalog/services/{service_id}` |
| Connector status/reconciliation | `GET /api/connectors/health`; `POST /api/outbox/{event_id}/reconcile` (admin) |
| Workflow job | `POST /api/workflows/briefs/{brief_id}/start`; `GET /api/workflows/{job_id}`, `/api/workflows/{job_id}/events` (SSE); `POST /api/workflows/{job_id}/resume`, `/api/workflows/{job_id}/cancel` |

Catalog service create/edit currently creates a new catalog version immediately; there is no separate draft/publish operation. Connector health reports `configured_unverified` rather than assuming that a configured provider is reachable. Workflow job routes and SSE are now declared, but durable recovery, cancellation and customer-response completion still need integration tests. `scripts/export_openapi.py` exported the current schema and `pnpm check:contract` passed on 2026-09-28 (26 route methods and 4 write payload shapes); this checks selected API shape, not every response type or a generated full client.

Quote version edits, internal review decisions, publication, and customer responses now serialize on the scoped quote row. A portal response rechecks its token and version after acquiring that lock, and a quote awaiting regeneration cannot publish an interim version. SQLite tests cover stale token replacement at the lock boundary and blocked interim publication; actual simultaneous requests against PostgreSQL remain to be tested. The expected-version/`If-Match` mutation contract below remains a target rather than an implemented request header.

Workflow start locks the brief and reuses that brief's active run even when another brief has a newer run in the same workspace. A local regression test covers the interleaved A–B–A start sequence; simultaneous PostgreSQL start requests remain to be tested.

## Common request and response rules

- Use stable, opaque IDs issued by the server; do not use IDs or LangGraph thread IDs as authorization.
- Use an idempotency key for acceptance and external-write requests. A repeated accepted request returns the existing state/handoff; a conflicting reuse of a key is an error.
- Quote mutations require an expected version or `If-Match` style guard. A stale version returns a conflict rather than overwriting an approval or accepted quote.
- Error responses should have a stable code, user-safe message, correlation ID and field errors where applicable. Never expose secrets, source content from another workspace or provider tokens.
- Long operations return a job/run ID whose status is persisted; SSE events report observable stages and tool outcomes, not hidden model reasoning.
- The typed TypeScript client is generated from or validated against the running OpenAPI schema. The exact generation/check command belongs in [`DEPENDENCIES.md`](DEPENDENCIES.md) once established.

## Contract checks

Integration tests should cover staff roles, workspace separation for every resource group, stale mutation rejection, token tampering/expiry/replacement, repeated acceptance, disconnected HubSpot and local outbox behavior. HubSpot contact/deal adapters need mock contract tests even when live credentials are absent. A local simulator must implement the same application-facing interface as the connected adapter.
