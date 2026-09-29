# ADR 0003: Version-bound commercial approval and customer review

**Status:** Accepted as business rule, 2026-09-28. Security tests remain unverified.

## Context

A human may approve a discount or noncatalog line, after which scope or price can change. A customer may retain an old review link. If approvals or links reference only a mutable quote ID, they could authorize a different commercial offer.

## Decision

Catalog versions and quote versions are immutable snapshots. Normalize approval-sensitive scope, pricing inputs and assumptions into a content hash. Approval references the exact quote version/hash. A customer review token binds one version, client, purpose and expiry; replacement or mutation invalidates acceptance of the old offer. Acceptance freezes that version and creates a uniquely keyed local handoff. Approval and external side effects are separate steps.

## Consequences

Revisions create new versions and require renewed approval when policy applies. Operators can compare a scope/price diff before asking for approval again. More records and token lifecycle logic are required, but the customer cannot silently accept a changed quote. Acceptance remains a workflow acknowledgement, not certified e-signature. Hash, token, concurrency and idempotency tests are mandatory.
