"""Gunicorn runs two workers; only the one holding the lock may start APScheduler,
otherwise every scheduled job (offline check, drift alerts) runs twice."""
import os

from app.core import scheduler_lock


class FakeFcntl:
    """flock semantics: an exclusive lock per path, released on close."""
    LOCK_EX = 2
    LOCK_NB = 4

    def __init__(self):
        self.held = set()

    def flock(self, handle, flags):
        path = os.path.abspath(handle.name)
        if path in self.held:
            raise BlockingIOError("locked")
        self.held.add(path)


def test_second_worker_does_not_get_the_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler_lock, "fcntl", FakeFcntl())
    path = str(tmp_path / "scheduler.lock")

    first = scheduler_lock.acquire_scheduler_lock(path)
    second = scheduler_lock.acquire_scheduler_lock(path)

    assert first is not None
    assert second is None
    first.close()


def test_platform_without_flock_always_runs_scheduler(tmp_path, monkeypatch):
    monkeypatch.setattr(scheduler_lock, "fcntl", None)

    assert scheduler_lock.acquire_scheduler_lock(str(tmp_path / "x.lock")) is not None
