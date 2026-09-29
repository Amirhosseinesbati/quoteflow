# QuoteFlow — independent portfolio case study

**Project type:** independent portfolio project using a fictional studio and synthetic demo data. **Verification status:** implementation and outcome claims must be taken from the evidence in [`EVALUATION.md`](EVALUATION.md) and [`HANDOVER.md`](HANDOVER.md). No customer result, revenue or time-saving figure has been measured or claimed here.

## Case study

Arc & Field Studio receives briefs that mix firm requests, vague preferences, missing assets and negotiation notes. A useful proposal must preserve what the client actually said, reveal uncertainties, present meaningful scope choices and keep the final price under human control. QuoteFlow is designed as a self-hostable proposal workspace that traces each supported requirement to its source, asks clarifying questions, builds three catalog-backed options and calculates prices with deterministic rules. An internal approval is tied to the exact quote version; the customer reviews that version and can accept, decline or request changes. Accepted versions become immutable handoff records.

The technical design separates model-written scope language from Decimal pricing, uses immutable catalog/quote versions for reproducibility, and treats customer links and external connector writes as security-sensitive workflows. The demo uses synthetic companies and a local outbox; a HubSpot adapter is a separate connected path. SQLite and Compose/PostgreSQL API smoke on 2026-09-28 exercised intake, analysis, clarification, three options, approval, PDF generation and acceptance with one handoff. Browser acceptance and a PostgreSQL workflow resumed after API restart were also verified locally. Connected-mode integrations and model quality remain unverified.

## 60–90 second demo script

1. **0–15 s:** Show the synthetic label and paste a messy fictional brief. Point to extracted requirements and source evidence; do not claim uncertain phrases as agreed scope.
2. **15–30 s:** Edit two targeted questions and answer them in the scoped customer view. Show the new brief revision.
3. **30–50 s:** Compare three distinct catalog-backed options, their inclusions, assumptions and deterministic totals. Request a discount beyond policy.
4. **50–65 s:** Show the version-bound approval queue, approved document preview and PDF. Change a requirement to show scope/price diff and approval invalidation.
5. **65–90 s:** Open the exact version's customer page, accept it, and show one handoff and simulated outbox entry. Repeat acceptance to demonstrate the same handoff, if the tested flow supports it.

Use this script only for steps actually working in the runnable demo; trim or identify pending steps in a live presentation.

## 3–5 minute technical walkthrough

1. **Problem/data (30–45 s):** Explain synthetic Arc & Field, source evidence, the fixed seed and held-out case split.
2. **Architecture (45–60 s):** Walk through API, domain pricing, versioned catalog, graph checkpoints, worker/outbox and local/HubSpot adapter boundary using [`ARCHITECTURE.md`](ARCHITECTURE.md).
3. **Main flow (60–90 s):** Run intake, clarification, options, approval and customer response. Show a scope diff and why approval is invalidated.
4. **Correctness/security (45–60 s):** Show Decimal rounding test, stale token rejection, cross-workspace guard and idempotent handoff test results if verified.
5. **Evidence/limits (30–45 s):** Show actual evaluation denominators, PDF/browser review and pending connected/human-review gates. Explain why synthetic results are not customer accuracy.

## Three content angles

- **Pricing under human control:** model-generated scope prose, versioned catalog and deterministic quote arithmetic.
- **Safe approval by version:** how scope changes invalidate approvals and customer links, with a diff the operator can inspect.
- **A realistic local demo:** synthetic scenarios, source evidence, local service simulators and explicit connected-mode boundaries.

## Screenshot inventory

These captures came from the real local browser journey on 2026-09-28 at 1440, 1024 and 390 px. The journey reached customer acceptance and a handoff. The proposal mobile and customer review images below are the final rechecked versions; the 390 px page was measured at 390 px with no horizontal overflow.

| Scene | Verified file |
| --- | --- |
| Brief intake | `screenshots/02-intake-1440.png` |
| Evidence | `screenshots/03-evidence-1440.png` |
| Clarifications | `screenshots/04-clarifications-1024.png` |
| Three option comparison | `screenshots/05-options-1440.png` |
| Approval queue | `screenshots/07-approval-1440.png` |
| Proposal mobile view | `screenshots/08-proposal-mobile-390-final.png` |
| Customer review | `screenshots/09-customer-review-1024-final.png` |
| Accepted mobile view | `screenshots/10-accepted-mobile-390-final.png` |

The scope diff and explicit error state are available in the UI/API workflow but are not represented in this eight-image set; capture those if needed for a fuller portfolio gallery.

## Resume bullet templates

These bullets use only recorded local evidence and must retain the independent/synthetic scope when used:

- Built an independent QuoteFlow pilot for fictional service-agency briefs; a local SQLite API smoke verified three scope options, a 15% discount approval, PDF generation and repeated acceptance yielding one handoff (2026-09-28).
- Generated a reproducible synthetic dataset with 35 catalog entries, 50 clients, 120 briefs, 180 versions across 80 quotes and 30 seeded handoffs; a fixture runner checked 90 cases split 30 development/60 held out with zero fixture integrity failures (2026-09-28).
- Checked the deterministic demo extractor on 30 held-out synthetic briefs: 60/60 evidence-span substring alignments, 30/30 explicit lead deliverables found and 30/30 exact matches for each of company, contact, email, timeline and budget. These checks do not measure semantic precision or connected-model quality.

No screenshot, semantic accuracy percentage, latency reduction, customer adoption or business result is asserted until the matching artifact exists.
