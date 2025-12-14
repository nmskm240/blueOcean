from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    credential: ApiCredential
    label: str


@dataclass(frozen=True)
class ApiCredential:
    exchange: str
    key: str
    secret: str
    is_sandbox: bool
