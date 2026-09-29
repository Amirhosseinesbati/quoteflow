"""Regression for workflow states longer than the original jobs.status column."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from quoteflow.models import Job


def test_job_status_migration_preserves_rows_and_fits_waiting_states():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "a4b1c9d2e3f4_widen_job_status.py"
    )
    spec = spec_from_file_location("widen_job_status", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "6b8d7ac31570"

    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    jobs = sa.Table(
        "jobs",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(jobs.insert().values(id="existing-job", status="running"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        column = next(
            item for item in sa.inspect(connection).get_columns("jobs") if item["name"] == "status"
        )
        expected_states = (
            "waiting_clarification",
            "waiting_internal_review",
            "waiting_publish_required",
            "waiting_customer_review",
            "cancel_requested",
        )
        assert column["type"].length == Job.__table__.c.status.type.length
        assert column["type"].length >= max(map(len, expected_states))
        saved_status = connection.execute(
            sa.text("SELECT status FROM jobs WHERE id = 'existing-job'")
        ).scalar_one()
        assert saved_status == "running"
