# QuoteFlow product contract

QuoteFlow is a proposal and quotation workspace for the fictional **Arc & Field Studio**. It turns an unstructured client brief into traceable requirements, clarification questions, three scope options, a deterministic price, an internally approved proposal, and a scoped customer review. It is an independent portfolio project and a configurable commercial pilot, not evidence of a deployed customer installation.

The product requirements in `../05-quoteflow.md` defines v1 requirements. This document describes the intended behavior; verified implementation is tracked in [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) and [`HANDOVER.md`](HANDOVER.md).

## People and access

| Role | Primary job | Boundary |
| --- | --- | --- |
| Admin | Configure workspace, catalog, tax/discount policy, connectors and users | One customer's installation; records remain workspace scoped |
| Operator | Review extraction, clarify scope, edit proposals, request approval and send for review | Cannot self-approve a restricted action unless also authorized as approver |
| Viewer | Inspect authorized briefs, quotes and audit events | Cannot change commercial state |
| Customer | Answer scoped questions and review one proposal version through a time-limited link | No account-wide or other-client access |

Demo workspaces, users, companies, prices and responses are synthetic. Demo notification and CRM writes use local adapters and are recorded as simulated actions. Connected mode uses configured model and HubSpot adapters; absent credentials or failed live requests must produce an explicit error, never a fake success.

## Main journey

1. An operator receives a form submission, pasted email, or text/PDF attachment. The original source and revisions remain available. Extraction identifies company/contact, deliverables, dates, budget, constraints, supplied assets and uncertainties, with evidence spans pointing back to source text. Vague wording stays uncertain.
2. The operator edits targeted clarification questions. A scoped customer link collects answers. A new answer creates a revision; regeneration updates affected sections and preserves prior versions for comparison.
3. A versioned service catalog supplies 35 demo entries across branding, website design, integrations and maintenance. Each of three distinct scope options maps every price-bearing line to a catalog service or an explicit noncatalog exception. Each line records quantity, price rule and assumptions.
4. The model may draft commercial prose. Server-side Decimal arithmetic calculates rates, discounts, configured contingency, tax and totals with an explicit rounding policy. The operator can edit the proposal, including summary, objectives, scope, deliverables, exclusions, assumptions, schedule, milestones, client responsibilities and acceptance steps.
5. Discounts above the configured threshold and noncatalog lines require internal approval tied to the exact quote version/content hash. A changed scope or price invalidates approval. An approved version can be rendered to branded PDF and assigned a version-scoped customer review token. Demo notifications enter a local outbox.
6. The customer may accept, decline or request revision. Acceptance is a workflow acknowledgement, **not a certified electronic signature**. Acceptance freezes the reviewed proposal version and creates one local handoff, even on a repeated request. Expired, replaced, modified or cross-client tokens cannot accept another version.

## Reviewable release criteria

- Complete local journey: brief → clarification → three valid options → version-bound approval → PDF → customer acceptance → one handoff.
- Pricing/rounding, discount policy, approval invalidation and accepted-version immutability tests pass.
- Held-out extraction reaches at least 95% precision and 90% recall for supported requirements; material invented requirements have a target of zero. Report each numerator, denominator and split. A target is not an achieved result.
- Stale, expired, cross-client and modified portal tokens fail closed; retries and connector uncertainty do not duplicate local handoffs.
- PDF text, line items, totals and pagination match the approved source version; CSV exports neutralize formula cells.
- Ten proposals receive a human rubric review for clarity, exclusions, feasibility and traceability. Without that review, the gate remains pending.
- Desktop and mobile flows are inspected at 1440, 1024 and 390 px, with 6–8 real screenshots including an error or review state.

## Deliberate v1 limits

The default deployment is one customer per installation, with workspace boundaries that can be tested using two seeded workspaces. Public self-service SaaS, certified e-signature, payment collection, accounting and CRM-specific pipelines are extensions. Sample proposal terms are configurable examples, not legal advice. Synthetic evaluation does not establish real-client accuracy or production readiness.
