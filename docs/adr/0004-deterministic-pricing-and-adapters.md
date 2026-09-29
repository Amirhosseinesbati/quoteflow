# ADR 0004: Deterministic pricing and explicit connector modes

**Status:** Accepted as implementation design, 2026-09-28. Adapter contracts and connected smoke tests remain unverified.

## Context

Model-drafted language is useful for readable proposals, but model output is unsuitable as an authoritative price. The demo must exercise the same business workflow as connected use without messaging real people or fabricating connected success.

## Decision

Use a versioned service catalog and a Decimal pricing function with explicit quantity, percentage discount, optional contingency/tax and rounding policy. Introduce `PricingStrategy` only if an actually different policy is added. Keep model prose separate from server-owned arithmetic. Give local CRM/outbox and HubSpot contacts/deals adapters the same application-facing interfaces. Select DEMO or CONNECTED explicitly in configuration. Missing credentials or a failed connected request produce an error or pending delivery state, never simulator success.

## Consequences

Prices are reproducible from catalog/quote versions and can be tested independently of model variability. Local demos are complete and safe, while connected integrations need separate credentials, controlled smoke tests and reconciliation for uncertain outcomes. Catalog editing requires validation and publication rather than editing rates inside prompts.
