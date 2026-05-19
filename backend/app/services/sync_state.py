from datetime import datetime, timezone
from typing import Any


class SyncState:
    def __init__(self) -> None:
        self.running = False
        self.phase = "idle"
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.total_repositories = 0
        self.synced_repositories = 0
        self.current_repository: str | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        self.running = True
        self.phase = "starting"
        self.started_at = _now()
        self.finished_at = None
        self.total_repositories = 0
        self.synced_repositories = 0
        self.current_repository = None
        self.last_error = None

    def finish(self) -> None:
        self.running = False
        self.phase = "idle"
        self.finished_at = _now()
        self.current_repository = None

    def fail(self, error: Exception) -> None:
        self.running = False
        self.phase = "failed"
        self.finished_at = _now()
        self.last_error = str(error)
        self.current_repository = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "phase": self.phase,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_repositories": self.total_repositories,
            "synced_repositories": self.synced_repositories,
            "current_repository": self.current_repository,
            "last_error": self.last_error,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


sync_state = SyncState()
