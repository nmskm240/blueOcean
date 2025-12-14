from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    id: AccountId
    credential: ApiCredential
    label: str


# region value_objects


@dataclass(frozen=True)
class AccountId:
    value: str | None

    @classmethod
    def empty(cls) -> "AccountId":
        return cls(value=None)

    def is_empty(self) -> bool:
        return self.value is None


@dataclass(frozen=True)
class ApiCredential:
    exchange: str
    key: str
    secret: str
    is_sandbox: bool
