"""Run APScheduler in exactly one gunicorn worker.

Every worker imports the app and fires the startup event, so without a lock
each scheduled job (offline-device check, drift detection, logger liveness)
runs once per worker — duplicate alerts racing each other's dedup. The first
worker to take an exclusive, non-blocking flock on a shared file runs the
scheduler; the OS releases the lock when that process exits, so a respawned
worker can take over.
"""
import os

try:
    import fcntl
except ImportError:  # Windows dev machines: single process, nothing to share
    fcntl = None

DEFAULT_LOCK_PATH = "/tmp/sparing-scheduler.lock"


class _NoLocking:
    """Stand-in handle where flock is unavailable."""

    def close(self) -> None:
        pass


def acquire_scheduler_lock(path: str | None = None):
    """Return a handle when this process should run the scheduler, else None.

    Keep the returned handle referenced for the process lifetime."""
    if fcntl is None:
        return _NoLocking()
    handle = open(path or os.environ.get("SCHEDULER_LOCK_PATH", DEFAULT_LOCK_PATH), "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle
