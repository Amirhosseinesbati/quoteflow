"""Long-lived, quiet worker for outbox delivery and expired workflow leases."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, suppress

from .config import get_settings
from .db import SessionLocal, engine
from .worker import process_outbox_once
from .workflow import build_workflow, make_checkpointer, recover_expired_jobs


def _close_checkpointer(manager: AbstractContextManager | None) -> None:
    if manager is not None:
        with suppress(Exception):
            manager.__exit__(None, None, None)


def run_worker(
    prepare_database: Callable[[], None],
    *,
    max_cycles: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Reuse imports/checkpointer; use a fresh SQLAlchemy session each cycle."""

    interval = max(1, get_settings().worker_poll_seconds)
    prepared = False
    checkpointer = None
    manager = None
    graph = None
    last_error: str | None = None
    cycles = 0
    try:
        while max_cycles is None or cycles < max_cycles:
            try:
                if not prepared:
                    prepare_database()
                    prepared = True
                if graph is None:
                    checkpointer, manager = make_checkpointer()
                    graph = build_workflow(checkpointer)
                # PostgresSaver holds one connection; detect a DB restart before
                # recovering a job so a stale checkpoint connection cannot fail it.
                connection = getattr(checkpointer, "conn", None)
                if connection is not None:
                    connection.execute("SELECT 1")
                with SessionLocal() as session:
                    outbox = process_outbox_once(session)
                    jobs = recover_expired_jobs(graph, session)
                if last_error is not None:
                    print(json.dumps({"event": "worker_reconnected"}), flush=True)
                    last_error = None
                if outbox.get("processed") or outbox.get("recovered_uncertain") or jobs:
                    print(
                        json.dumps(
                            {
                                "event": "worker_activity",
                                "outbox_processed": outbox.get("processed", 0),
                                "outbox_status": outbox.get("status"),
                                "recovered_uncertain": outbox.get("recovered_uncertain", 0),
                                "jobs": [
                                    {"id": job["id"], "status": job["status"]} for job in jobs
                                ],
                            }
                        ),
                        flush=True,
                    )
            except Exception as exc:
                error_type = type(exc).__name__
                if error_type != last_error:
                    print(
                        json.dumps(
                            {
                                "event": "worker_retrying",
                                "error_type": error_type,
                                "retry_seconds": interval,
                            }
                        ),
                        file=sys.stderr,
                        flush=True,
                    )
                last_error = error_type
                _close_checkpointer(manager)
                checkpointer = manager = graph = None
                with suppress(Exception):
                    engine.dispose()
            cycles += 1
            if max_cycles is None or cycles < max_cycles:
                sleep_fn(interval)
    finally:
        _close_checkpointer(manager)
