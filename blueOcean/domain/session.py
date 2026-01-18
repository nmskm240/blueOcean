from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field

from cuid2 import Cuid


@dataclass
class Session:
    id: SessionId = field(default_factory=lambda: SessionId())
    name: str = field(default="")

    def rename(self, name: str):
        self.name = name


# region value_objects


@dataclass(frozen=True)
class SessionId:
    value: str = field(default_factory=Cuid().generate)


# region interfaces


class ISessionRepository(metaclass=ABCMeta):
    @abstractmethod
    def get_all(self) -> list[Session]:
        raise NotImplementedError()

    @abstractmethod
    def find_by_id(self, id: SessionId) -> Session:
        raise NotImplementedError()

    @abstractmethod
    def find_by_ids(self, *ids: SessionId) -> list[Session]:
        raise NotImplementedError()

    @abstractmethod
    def save(self, session: Session) -> Session:
        raise NotImplementedError()
