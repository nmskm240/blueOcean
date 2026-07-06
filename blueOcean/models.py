from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from cuid2 import Cuid


@dataclass(frozen=True)
class AccountId:
    value: str

    @classmethod
    def create(cls) -> AccountId:
        return cls(Cuid().generate())
    
@dataclass(frozen=True)
class Mt5Connection:
    path: str
    server: str
    login: int
    encrypted_password: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise ValueError("MT5端末のローカルパスは必須です")
        if "://" in self.path or not (
            PureWindowsPath(self.path).is_absolute()
            or PurePosixPath(self.path).is_absolute()
        ):
            raise ValueError("MT5端末には絶対ローカルパスを指定してください")
        if not isinstance(self.server, str) or not self.server.strip():
            raise ValueError("MT5サーバー名は必須です")
        if not isinstance(self.login, int) or isinstance(self.login, bool) or self.login <= 0:
            raise ValueError("MT5ログインIDは正の整数である必要があります")
        if not isinstance(self.encrypted_password, bytes) or not self.encrypted_password:
            raise ValueError("暗号化済みMT5パスワードは必須です")


class Account:
    def __init__(self, name: str, connection: Mt5Connection, portable: bool, id: AccountId = None):
        self.id = id if id is not None else AccountId.create()
        self.name = name
        self.connection = connection
        self.portable = portable

    @property
    def has_password(self) -> bool:
        return bool(self.connection.encrypted_password)


class AccountNotFoundError(LookupError):
    pass
    
class IAccountRepository(metaclass=ABCMeta):
    """Interface for persisting domain ``Account`` objects without interpreting credentials."""

    @abstractmethod
    def list(self) -> list[Account]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, id: AccountId) -> Account:
        raise NotImplementedError

    @abstractmethod
    def save(self, account: Account) -> AccountId:
        raise NotImplementedError

    @abstractmethod
    def delete_by_id(self, id: AccountId) -> None:
        raise NotImplementedError
