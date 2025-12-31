from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any

from cuid2 import Cuid


class PlaygroundRunStatus(IntEnum):
    SUCCESS = 1
    FAILED = 2


@dataclass(frozen=True)
class PlaygroundRunId:
    value: str

    @classmethod
    def create(cls) -> PlaygroundRunId:
        return cls(Cuid().generate())


@dataclass
class PlaygroundRun:
    id: PlaygroundRunId
    notebook_path: str
    parameters: dict[str, Any]
    markdown: str
    status: PlaygroundRunStatus
    executed_at: datetime
    output_path: str | None = None
    error_message: str | None = None


class IPlaygroundRunRepository(metaclass=ABCMeta):
    @abstractmethod
    def save(self, run: PlaygroundRun) -> PlaygroundRun:
        raise NotImplementedError()

    @abstractmethod
    def find_by_id(self, run_id: PlaygroundRunId) -> PlaygroundRun:
        raise NotImplementedError()

    @abstractmethod
    def get_all(self) -> list[PlaygroundRun]:
        raise NotImplementedError()
