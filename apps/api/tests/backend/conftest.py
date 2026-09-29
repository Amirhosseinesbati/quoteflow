from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from quoteflow.config import get_settings
from quoteflow.db import Base, get_db
from quoteflow.main import app
from quoteflow.seed import seed_demo


@pytest.fixture
def api(tmp_path, monkeypatch) -> Generator[tuple[TestClient, sessionmaker], None, None]:
    monkeypatch.setenv("MODE", "DEMO")
    monkeypatch.setenv("ASSET_DIR", str(tmp_path / "assets"))
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        seed_demo(db)

    def override_db() -> Generator[Session, None, None]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    yield client, factory
    client.close()
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    engine.dispose()
