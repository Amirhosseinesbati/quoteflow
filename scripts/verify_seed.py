"""Check full DEMO database counts and workspace boundaries after init-demo --full."""

from __future__ import annotations

from sqlalchemy import func, select

from quoteflow.db import SessionLocal
from quoteflow.models import (
    Brief, Client, ProjectHandoff, Quote, QuoteVersion, ServiceCatalogEntry,
    User, Workspace,
)


def main() -> None:
    expected = {"workspaces": 2, "users": 6, "catalog_entries": 70, "clients": 50,
                "briefs": 120, "quotes": 80, "quote_versions": 180, "handoffs": 30}
    models = {"workspaces": Workspace, "users": User, "catalog_entries": ServiceCatalogEntry,
              "clients": Client, "briefs": Brief, "quotes": Quote,
              "quote_versions": QuoteVersion, "handoffs": ProjectHandoff}
    with SessionLocal() as db:
        actual = {name: db.scalar(select(func.count()).select_from(model)) for name, model in models.items()}
        for name, count in expected.items():
            if actual[name] != count:
                raise AssertionError(f"{name}: expected {count}, found {actual[name]}")
        for workspace_id, expected_clients in (("arc-field-demo", 40), ("arc-field-isolation", 10)):
            count = db.scalar(select(func.count()).select_from(Client).where(Client.workspace_id == workspace_id))
            if count != expected_clients:
                raise AssertionError(f"{workspace_id}: expected {expected_clients} clients, found {count}")
    print(actual)


if __name__ == "__main__":
    main()
