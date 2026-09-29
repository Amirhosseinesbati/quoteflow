# Commercial pilot notes

QuoteFlow can be packaged as a configurable quoting assistant for service businesses that repeatedly turn messy requests into scoped, priced proposals. The initial fictional vertical is Arc & Field Studio, a web/design agency. This is an independent portfolio build; there is no claim of real customers, sales or validated business impact.

## Ideal first buyer and offer

The first buyer is a small design, web or digital service studio with a stable service menu, an owner/operations approver and enough quote volume to benefit from consistent scope review. The offer is a customer-specific installation plus catalog/terms configuration, staff training and controlled connector setup. It should be sold as a pilot with measured acceptance criteria, not as a fully automated salesperson or legally binding e-signature platform.

## Onboarding sequence

1. Confirm hosting region, data retention, roles, responsible approver, support contact and a spending limit for model use.
2. Import and verify service catalog entries, quantities, rate rules, discount threshold, contingency/tax policy, currency and rounding. Preserve catalog versions so old quotes remain reproducible.
3. Configure branding, sample proposal terms, review expiry and customer-facing language with the buyer; obtain their own legal review of terms.
4. Set up workspace/user accounts and backup destination, then import a small sample of historical briefs with consent and retention controls.
5. Run local end-to-end acceptance, PDF review, cross-workspace/token tests, backup/restore smoke test and an operator training scenario.
6. If HubSpot is needed, configure least-privilege credentials in CONNECTED mode, test against controlled contacts/deals, set reconciliation process and monitor first deliveries.
7. Agree on success metrics such as time to reviewed proposal and revision count; measure a baseline and pilot results before making outcome claims.

## Deployment prerequisites

A buyer needs an isolated installation, PostgreSQL, asset storage, TLS termination, secret management, backup/restore capability, outbound access for configured model/HubSpot connectors, domain/email arrangements for real notifications if added, and an operator responsible for approval. The local demo uses synthetic workspaces and local simulated outbox/CRM. Production notification delivery is not included unless separately implemented and verified.

## Reusable modules

The most reusable boundaries are versioned catalog and Decimal pricing, quote/content hashing, approval policy, proposal PDF rendering, review portal tokens, durable outbox/reconciliation, and source evidence extraction. Each should expose a small contract so a later service business can replace catalog rules, terms and branding without copying a full product.

## Cost model

Estimate costs with customer-specific inputs, not a fixed unsupported market figure:

| Cost | Configurable estimate |
| --- | --- |
| Model use | `monthly_briefs × average_input_tokens × input_price + monthly_briefs × average_output_tokens × output_price`, plus regeneration and review calls. Use provider's current price sheet and record model ID. |
| Database and storage | PostgreSQL instance + retained briefs/PDF/assets + backup copies, based on hosting quote and retention period. |
| HubSpot | Customer's account tier and API limits; verify in their account. |
| Hosting/operations | API/web/worker compute, monitoring, TLS, backup restore drills, upgrades and support time. |
| Implementation | One-time catalog mapping, brand/terms configuration, integration testing, migration and training. |

No cost estimate is claimed until model/provider rates, volume and hosting choice are supplied and calculated. Server logs should show known token usage and mark unknown provider costs explicitly.

## Supported integrations and v1 limits

The required connector contract is local CRM/outbox simulation and HubSpot contacts/deals. Live verification depends on external credentials and a controlled test account. Certified e-signature, payments, accounting, public self-service tenancy and CRM-specific sales pipelines are outside v1. A review-page acceptance is a product acknowledgement only. Synthetic extraction quality does not predict customer accuracy without a real-data pilot.

## Redistribution review

Before distributing an installation or source bundle, check actual licenses for locked dependencies, fonts, icons, images and templates; retain required notices and verify that any third-party brand assets are customer-provided with rights. A direct-package metadata inventory is in [`LICENSE_AUDIT.md`](LICENSE_AUDIT.md), with transitive packages, base images and final notices still to review. No third-party resale or asset rights are claimed by that inventory.
