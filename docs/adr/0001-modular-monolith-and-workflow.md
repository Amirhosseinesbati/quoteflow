# ADR 0001: Modular monolith with a bounded quote workflow

**Status:** Accepted as implementation design, 2026-09-28. Runtime integration is tracked separately.

## Context

QuoteFlow has one business domain with closely related brief, quote, approval and handoff transactions. It also has an explicit sequence with human pauses and revisions. Splitting each step into a separate service would add deployment and consistency costs before a pilot has demonstrated that need.

## Decision

Use one FastAPI application with capability-focused modules, a small durable worker and one web client. Domain functions own pricing and state rules. Use LangGraph `StateGraph` for explicit stage transitions, human interrupts and resumable workflow coordination. Graph nodes call application use cases; they do not recalculate prices or embed SQL/HTTP concerns. Use LangChain for the model adapter and validated structured output, without an autonomous agent loop for a fixed transformation.

## Consequences

The application can transact quote state and outbox claims in one database. The graph adds checkpoint/recovery semantics but must have bounded steps, retries and cost. A single deployment can become a scaling limit if throughput grows; worker count can be increased before splitting services. A local PostgreSQL workflow resumed after API restart and recorded 16 checkpoints; a manually expired lease was recovered by the worker. Actual process-crash and concurrent-worker tests remain release gates.
