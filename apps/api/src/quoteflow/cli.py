from __future__ import annotations

import argparse
import json
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect

from alembic import command

from . import models  # noqa: F401
from .db import Base, SessionLocal, engine
from .seed import seed_demo


def initialize_schema() -> None:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    tables = set(inspect(engine).get_table_names())
    if tables and "alembic_version" not in tables:
        if set(Base.metadata.tables).issubset(tables):
            columns = {column["name"] for column in inspect(engine).get_columns("outbox_events")}
            line_columns = {column["name"] for column in inspect(engine).get_columns("quote_lines")}
            if "next_attempt_at" in columns and "position" in line_columns:
                job_status = next(
                    column for column in inspect(engine).get_columns("jobs")
                    if column["name"] == "status"
                )
                revision = (
                    "head"
                    if (getattr(job_status["type"], "length", 0) or 0) >= 64
                    else "6b8d7ac31570"
                )
            elif "next_attempt_at" in columns:
                revision = "23d641a63a5f"
            elif {"attempts", "last_error", "provider_id", "lease_until"}.issubset(columns):
                revision = "f111a98e0e1c"
            else:
                revision = "75a6d9e57e63"
            command.stamp(config, revision)  # Legacy local create_all bootstrap only.
        else:
            raise RuntimeError("Partial database schema has no Alembic revision")
    command.upgrade(config, "head")


def main() -> None:
    parser = argparse.ArgumentParser(description="QuoteFlow database maintenance")
    parser.add_argument("command", choices=["init-demo", "process-outbox", "run-worker"])
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--data-path", type=Path)
    args = parser.parse_args()
    if args.command == "run-worker":
        from .worker_runner import run_worker

        run_worker(initialize_schema)
        return
    initialize_schema()
    with SessionLocal() as session:
        if args.command == "init-demo":
            print(json.dumps(seed_demo(session, full=args.full, data_path=args.data_path)))
        else:
            from .worker import process_outbox_once
            from .workflow import build_workflow, make_checkpointer, recover_expired_jobs

            outbox = process_outbox_once(session)
            checkpointer, manager = make_checkpointer()
            try:
                jobs = recover_expired_jobs(build_workflow(checkpointer), session)
            finally:
                if manager is not None:
                    manager.__exit__(None, None, None)
            print(json.dumps({"outbox": outbox, "recovered_jobs": jobs}))


if __name__ == "__main__":
    main()
