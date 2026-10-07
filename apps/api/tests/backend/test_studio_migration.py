"""Upgrade the previous schema without touching workspace or quote records."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory


def test_workspace_preferences_migration_is_single_head_and_preserves_workspaces():
    api_root = Path(__file__).resolve().parents[2]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "alembic"))
    assert ScriptDirectory.from_config(config).get_heads() == ["d62af884a315"]
    path = api_root / "alembic/versions/d62af884a315_workspace_preferences.py"
    spec = spec_from_file_location("workspace_preferences_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE workspaces (id VARCHAR(36) PRIMARY KEY, name VARCHAR(160))"))
        connection.execute(sa.text("INSERT INTO workspaces VALUES ('existing', 'Existing Studio')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert connection.execute(sa.text("SELECT name FROM workspaces")).scalar_one() == "Existing Studio"
        assert "workspace_preferences" in sa.inspect(connection).get_table_names()
        assert connection.execute(sa.text("SELECT COUNT(*) FROM workspace_preferences")).scalar_one() == 0
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert "workspace_preferences" not in sa.inspect(connection).get_table_names()
        assert connection.execute(sa.text("SELECT name FROM workspaces")).scalar_one() == "Existing Studio"
