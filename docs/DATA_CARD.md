# Synthetic demo dataset card

**Status:** The generator and fixture integrity runner completed on 2026-09-28 with the requested top-level counts and 30/60 evaluation split. The runner reports `checks_passed: true` and zero fixture failures in `evals/results/fixture.json`. Fresh SQLite and PostgreSQL databases were full-seeded and queried: 2 workspaces, 6 users, 70 catalog entries (35 per workspace), 50 clients, 120 briefs, 80 quotes, 180 versions and 30 handoffs. PostgreSQL migration later reached `a4b1c9d2e3f4`. Behavioral access coverage and live-model quality remain separate gates.

## Purpose and provenance

The dataset portrays the fictional Arc & Field Studio and fictional buyers for local demonstration, development and held-out evaluation. It is labeled **Synthetic demo dataset** in UI and exports. Company identities, contact addresses and project histories are invented. Addresses use `example.com` or `.test`, and IDs are fictional. Prices are derived from the project's configurable fictional catalog; they are not market rates, customer contracts or revenue claims.

| Entity | Full-data target | Relationships and variation |
| --- | ---: | --- |
| Service catalog entries | 35 | Branding, website design, integrations and maintenance; versioned price rules. |
| Clients | 50 | Different sectors, contact completeness and asset availability. |
| Briefs | 120 | Varied length, wording, quality, budget and timeline constraints. |
| Quote records | 80 | Each belongs to a client and brief. |
| Quote versions | 180 | Revisions, scope changes, discount requests and approval invalidation. |
| Accepted handoffs | 30 | Exactly one per accepted quote version, with related customer response. |
| Authored substantial briefs | At least 12 | Detailed enough for convincing 2–4 page proposal drafts. |
| Evaluation cases | 90 | 40 extraction/scope, 30 pricing/rounding/revision, 20 approval/token/access/retry. |

The generator uses seed `90421` and reference date `2026-09-28` by default; both are configurable. It includes 12 authored scenario narratives, then varies openings, follow-ups and planted anomalies across 120 briefs. A fast seed supports local startup; the full generator reproduces acceptance data. The 12 narratives and generated proposals still need human review for the requested 2–4 page quality, and repeated template structure is a synthetic-data limitation.

## Observed generated distribution

The catalog contains 8 branding, 12 website design, 8 integration and 7 maintenance entries. Each of the 12 scenario templates is used for 10 briefs; sources are 40 public forms and 80 pasted emails. The 50 clients are split between two synthetic workspace IDs (40 in the main demo workspace and 10 in the isolation workspace). Among the 80 quotes, 20 have three seeded versions and 60 have two, giving 180 versions. The 30 handoffs correspond to accepted seeded quotes. These are generator/file facts, not usage statistics. Text/PDF upload is a runtime journey and is not represented by these seeded brief source types.

## Planned edge cases

Contradictory dates, unclear quantities, missing brand assets, very tight budgets, discount requests, noncatalog services, repeated intake, duplicated contacts, sparse source material and expanded scope after approval are deliberately planted. Missing fields remain missing rather than being filled by the model. Scenario structure determines labels and arithmetic ground truth; the model being evaluated never supplies its own answer key.

## Split and leakage controls

The intended evaluation split is 30 development and 60 held-out cases. Assign by client/entity and brief template before model evaluation so near duplicates do not cross splits. Keep held-out labels and scenario answers outside prompt modules, retrieval indexes and runtime API responses. If examples are stored near application fixtures, the loader must explicitly exclude answer keys. Record split identifiers and any temporal boundary in the generator manifest. Model or prompt edits informed by held-out errors require a fresh held-out set or must be reported as contaminated evaluation.

## Integrity checks

The full-data run should verify foreign keys, unique/version ordering, timeline order, accepted-state consistency, quote line arithmetic, service catalog references, handoff uniqueness, absence of real domains, and expected counts. Catalog totals and discounts should be recalculated independently from serialized quote totals. The demo reset must target only the demo namespace, leaving connected/customer records untouched.

## Known limitations

Synthetic briefs cannot capture the diversity of real customers, attachment quality, negotiation history or legal terms. Prices are fictional. Seeded acceptance events do not establish that a real buyer accepted a proposal. Synthetic precision/recall and rubric reviews are pilot evidence only, not a production accuracy promise.

## Verification record

| Item | Actual value | Evidence |
| --- | --- | --- |
| Fixed seed and reference date | `90421`; `2026-09-28` | `data/generated/metadata.json` inspected 2026-09-28 |
| Full generation command and date | `python scripts/generate_demo.py --output data/generated` on 2026-09-28 | Ran on bundled Python 3.12.13 |
| Actual file counts | 35 catalog; 50 clients; 120 briefs; 80 quotes; 180 versions; 30 handoffs | `evals/results/fixture.json` |
| Actual SQLite rows | 2 workspaces; 6 users; 70 catalog entries (35 each); 50 clients; 120 briefs; 80 quotes; 180 versions; 30 handoffs | Fresh SQLite migration through `6b8d7ac31570` + `python -m quoteflow.cli init-demo --full` + `scripts/verify_seed.py` on 2026-09-28 |
| Actual PostgreSQL seeded rows | 2 workspaces; 6 users; 70 catalog entries; 50 clients; 120 briefs; 80 quotes; 180 versions; 30 handoffs | Compose/PostgreSQL 17.10 full seed on 2026-09-28, then migration through `a4b1c9d2e3f4`; later smoke/workflow runs added records, so these are initial seed counts |
| Actual evaluation split | 90 cases: 30 development, 60 held out; categories 40/30/20 | `evals/results/fixture.json` and `data/generated/evaluation_only/cases.json`; extraction cases split by scenario template and client |
| Fixture integrity checks | Passed; zero failures | `python evals/run.py --mode fixture` on 2026-09-28; behavioral cases are definitions only in fixture mode |
