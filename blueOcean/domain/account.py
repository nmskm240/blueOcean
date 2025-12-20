from __future__ import annotations

from dataclasses import dataclass

from cuid2 import Cuid


@dataclass
class Account:
    id: AccountId
    credential: ApiCredential
    label: str


# region value_objects


@dataclass(frozen=True)
class AccountId:
    value: str

    @classmethod
    def create(cls) -> AccountId:
        return cls(Cuid().generate())


@dataclass(frozen=True)
class ApiCredential:
    exchange: str
    key: str
    secret: str
    is_sandbox: bool
