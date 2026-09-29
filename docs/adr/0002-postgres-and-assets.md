# ADR 0002: PostgreSQL for durable state, scoped storage for assets

**Status:** Accepted as implementation design, 2026-09-28. Separate database and local asset restore checks passed; coordinated restore remains unverified.

## Context

Quote versions, approvals, portal responses and outbox delivery must survive retries and support uniqueness/transactional claims. Workflow checkpoints are durable but are not an application job queue or a substitute for business records. PDFs and uploaded briefs can be too large for graph state.

## Decision

Use PostgreSQL for domain records, job leases/outbox and LangGraph checkpoints. Keep uploaded documents and generated PDFs in scoped asset storage, referenced by opaque IDs. Do not add a second database or vector store in v1 without a retrieval requirement. Back up database, checkpoint state and asset storage as one recoverable installation.

## Consequences

One database reduces local setup and cross-store consistency burden. Asset access requires explicit workspace checks and coordinated backup/restore. A database outage affects workflow and business writes together, so health checks and recovery procedures are mandatory. A custom-format database dump restored matching rows/checkpoints to a separate DB, and three PDF files matched after local tar/extraction to another directory. A coordinated DB-plus-asset restore into a separate installation and backup encryption remain unverified.
