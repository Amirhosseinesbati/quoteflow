"""The worker keeps one setup alive and reconnects after a stale checkpoint."""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from quoteflow import worker_runner


def test_persistent_worker_reuses_setup_and_sessions_then_reconnects(monkeypatch, capsys):
    prepared = []
    checkpoints = []
    managers = []
    sessions = []
    sleeps = []
    disposals = []

    class Checkpointer:
        def __init__(self, number):
            self.number = number
            self.conn = self
            self.pings = 0

        def execute(self, query):
            assert query == "SELECT 1"
            self.pings += 1
            if self.number == 1 and self.pings == 2:
                raise ConnectionError("stale checkpoint connection")

    class Manager:
        def __init__(self):
            self.closed = 0

        def __exit__(self, *_):
            self.closed += 1

    def make_checkpointer():
        checkpoint = Checkpointer(len(checkpoints) + 1)
        manager = Manager()
        checkpoints.append(checkpoint)
        managers.append(manager)
        return checkpoint, manager

    def session_local():
        session = object()
        sessions.append(session)
        return nullcontext(session)

    monkeypatch.setattr(
        worker_runner, "get_settings", lambda: SimpleNamespace(worker_poll_seconds=10)
    )
    monkeypatch.setattr(worker_runner, "make_checkpointer", make_checkpointer)
    monkeypatch.setattr(worker_runner, "build_workflow", lambda checkpoint: checkpoint)
    monkeypatch.setattr(worker_runner, "SessionLocal", session_local)
    monkeypatch.setattr(worker_runner, "engine", SimpleNamespace(dispose=lambda: disposals.append(1)))
    monkeypatch.setattr(
        worker_runner, "process_outbox_once", lambda session: {"processed": 0}
    )
    monkeypatch.setattr(worker_runner, "recover_expired_jobs", lambda graph, session: [])

    worker_runner.run_worker(
        lambda: prepared.append(1),
        max_cycles=3,
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )

    output = capsys.readouterr()
    assert len(prepared) == 1
    assert len(checkpoints) == 2
    assert len(sessions) == 2
    assert [manager.closed for manager in managers] == [1, 1]
    assert len(disposals) == 1
    assert sleeps == [10, 10]
    assert "worker_activity" not in output.out
    assert output.out.count("worker_reconnected") == 1
    assert output.err.count("worker_retrying") == 1
