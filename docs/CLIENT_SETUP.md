# Configure QuoteFlow for a client

This guide covers the local, self-hosted pilot and its proposal workbench. Synthetic tests demonstrate workflow behavior, not live model quality or production readiness. See the [design and theme report](WORKBENCH_2026-10-07.md) for the latest interface verification.

## Run a local preview without Docker

With the existing locked Python and web dependencies installed, run from the QuoteFlow root:

```powershell
.\scripts\preview-local.ps1
```

Open `http://127.0.0.1:4316`. The API listens on `127.0.0.1:8316`. The script initializes a migrated SQLite demo, places its database/assets/logs under ignored `tmp/client-preview`, disables API access logs, and starts the frontend. Press Ctrl+C to stop. Change ports with `-WebPort` and `-ApiPort` when needed. This preview uses the minimal synthetic seed and keeps its data between runs. It does not exercise PostgreSQL checkpoints, concurrent row locks, Docker, or connected providers.

## Set the studio defaults

Use **Appearance** on the entry screen, studio toolbar, or customer portal to select **Light**, **Dark**, or **System**. The browser retains the choice; System follows the operating system live. A fresh or invalid preference defaults to Dark. With storage blocked, the current choice remains usable until reload. Appearance changes keep current form edits, calculated pricing, and workflow state. Proposal documents and exported PDFs keep their fixed printable colors.

Enter the synthetic workspace as **admin** and open **Studio settings**. Operators and viewers can inspect and export defaults, but the API permits only an admin to save them. Settings belong to the signed-in workspace. They persist in the database, including across sign out and server restart.

| Setting | Behavior |
| --- | --- |
| Studio name and document accent | Used in newly generated proposal previews and PDFs |
| Currency | USD, EUR, GBP, CAD, AUD, or CHF; amounts retain two decimal places |
| Tax label and default tax | Set the displayed label and starting percentage for new options |
| Default contingency | Applied to the subtotal after the discount, before tax |
| Review discounts above | Discounts strictly above this percentage require internal approval; noncatalog items also require review |
| Proposal title and summary | Support literal `{studio}`, `{client}`, and `{package}` placeholders |
| Terms and footer | Copied into new options; proposal terms can then be edited per version |

Currency is a label for catalog rates. Changing USD to EUR does **not** convert prices. Review or replace the rates before generating the customer's first options. The price engine applies discount first, then contingency, then tax on the discounted amount plus contingency, rounding each amount to two decimal places. Quote edits use the current workspace review threshold. This is a configurable operational calculation, not a determination of the customer's tax obligations.

Saving defaults does not rewrite proposals. A generated option contains a frozen `_document` snapshot inside its content hash. Its brand, currency, document title, and tax label stay with that version through edits, approval, publication, and acceptance. To use new defaults, regenerate options; earlier unaccepted versions and their customer links are superseded. Existing accepted quotes remain immutable. Historical proposals created before this feature keep the original Arc & Field/USD identity when revised.

Two admins saving from the same revision cannot silently overwrite each other: the later stale request returns 409 and asks for a reload. PostgreSQL uses a workspace row lock; simultaneous PostgreSQL writes have not been tested in this local SQLite run.

## Reuse a template

**Export template** downloads a JSON file containing branding, pricing defaults, and text defaults only. It contains no credentials, client briefs, contacts, quote IDs, or catalog service rows. **Import template** validates the file shape and loads a draft; review it and select **Save studio settings** to persist it. Invalid files remain unapplied. Exports use `schema_version: 1` and imports are limited to 24 KB. The API performs authoritative field validation when the draft is saved.

Use the exported file to initialize another installation's studio. Review the template's rates assumptions and terms for that customer. This is a studio-default template, not an import of quotes or a full workspace backup.

## Customize the catalog

An admin can add/edit services, create customer-specific categories, set units/rates, and deactivate services. Every successful change creates a catalog version. Search and category filters include custom categories. Proposal editing queries its own historical catalog version, so its service IDs and rates do not silently switch to today's catalog. Generate fresh options to adopt new catalog rates.

The demo matcher recognizes the supplied catalog codes and uses text matching for custom service names. Quantity estimates and option selection still need human review. This pass does not implement bulk catalog import, a catalog currency conversion, or a full template for matching/quantity rules.

## Review and hand off

1. Create and analyze a brief. Review its source evidence and answer open clarifications.
2. Generate three catalog-priced options and inspect scope, exclusions, assumptions, terms, and totals.
3. Edit scope/pricing if necessary. Saving creates a new version and invalidates earlier approvals and review links. Sharing is disabled while local edits are unsaved.
4. Request approval when required. An admin approves the exact version. A changed scope/price/terms needs a fresh decision.
5. Generate the PDF and review link. The PDF button becomes available after publication. Replacing the link invalidates the previous link for the same version.
6. The customer reviews through a scoped bearer link. Acceptance freezes the version and creates one handoff; a repeated acceptance returns the same handoff.

The customer response dialog supports keyboard focus containment and Escape. Review links are bearer credentials: send them only through an authorized channel and avoid including them in logs. Demo notifications are recorded locally. Publication does not claim delivery by an external provider. Acceptance is a workflow acknowledgement, not a certified electronic signature.

## Auth and deployment limits

The DEMO role picker is deliberately available without a password only when the API reports DEMO. Reload restores the existing HTTP-only server session; it does not issue a fresh privileged session from a stored role preference. Sign out revokes the server session and clears workspace query data. Expired sessions return to entry. Connected mode displays password sign-in for an account provisioned by the administrator; demo sessions and demo password accounts are blocked there by the API.

Customer user provisioning, SSO/MFA, production host/proxy security, live connector tests, PostgreSQL concurrency, coordinated backups, multilingual PDF fonts, and legal/commercial terms review remain deployment work. Built-in PDF fonts support the current Latin fixtures; Persian or other non-Latin PDF output is not verified. Do not advertise a secure customer launch based on the demo role picker or this SQLite run.

## Schema and API

Migration `d62af884a315` follows `a4b1c9d2e3f4` and adds `workspace_preferences`. Upgrade an existing migrated installation with the normal `python -m quoteflow.cli init-demo` path in demo mode, or `alembic upgrade head` under the configured production database. Do not seed synthetic data into a customer database. The demo preview script scopes initialization to its own SQLite file.

- `GET /api/studio-settings`: current workspace defaults and integer revision; requires a staff session.
- `PUT /api/studio-settings`: `{ "settings": { ... }, "expected_revision": 0 }`; admin only; returns saved defaults and new revision.
- `GET /api/catalog?version_id=<id>`: authenticated, workspace-scoped historical catalog.

No secrets belong in these payloads. Configure live provider secrets server-side and run controlled integration checks separately.
