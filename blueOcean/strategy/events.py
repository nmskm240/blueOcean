from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RunnerEvent:
    kind: str
    occurred_at: datetime
    error: str | None = None
    result: dict | None = None
