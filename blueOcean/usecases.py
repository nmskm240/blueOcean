from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet
from injector import inject

from blueOcean.models import Account, AccountId, IAccountRepository, Mt5Connection
from blueOcean.metatrader.workers import MT5WorkerManager, WorkerStatus


class AccountWorkerActiveError(RuntimeError):
    pass


def ensure_account_is_editable(manager: MT5WorkerManager, account_id: AccountId) -> None:
    status = manager.get_status(account_id.value)
    if status.state in ("starting", "running"):
        raise AccountWorkerActiveError(
            f"MT5が{status.state}の間はアカウント設定を変更できません"
        )


@dataclass(frozen=True)
class CreateAccountInput:
    name: str
    path: str
    login: int
    password: str
    server: str
    portable: bool


@dataclass(frozen=True)
class UpdateAccountInput:
    account_id: AccountId
    name: str
    path: str
    login: int
    password: str
    server: str
    portable: bool


class CreateAccountUseCase:
    @inject
    def __init__(self, repository: IAccountRepository, cipher: Fernet) -> None:
        self._repository = repository
        self._cipher = cipher

    def execute(self, input: CreateAccountInput) -> Account:
        account = Account(
            name=input.name,
            connection=Mt5Connection(
                path=input.path,
                server=input.server,
                login=input.login,
                encrypted_password=self._cipher.encrypt(input.password.encode()),
            ),
            portable=input.portable,
        )
        saved_id = self._repository.save(account)
        return self._repository.get_by_id(saved_id)


class ListAccountsUseCase:
    @inject
    def __init__(self, repository: IAccountRepository) -> None:
        self._repository = repository

    def execute(self):
        return self._repository.list()


class GetAccountUseCase:
    @inject
    def __init__(self, repository: IAccountRepository) -> None:
        self._repository = repository

    def execute(self, account_id: AccountId) -> Account:
        return self._repository.get_by_id(account_id)


class UpdateAccountUseCase:
    @inject
    def __init__(
        self, repository: IAccountRepository, cipher: Fernet, manager: MT5WorkerManager
    ) -> None:
        self._repository = repository
        self._cipher = cipher
        self._manager = manager

    def execute(self, input: UpdateAccountInput) -> Account:
        ensure_account_is_editable(self._manager, input.account_id)
        current = self._repository.get_by_id(input.account_id)
        encrypted_password = (
            self._cipher.encrypt(input.password.encode())
            if input.password
            else current.connection.encrypted_password
        )
        account = Account(
            id=current.id,
            name=input.name,
            connection=Mt5Connection(
                path=input.path,
                server=input.server,
                login=input.login,
                encrypted_password=encrypted_password,
            ),
            portable=input.portable,
        )
        self._repository.save(account)
        return self._repository.get_by_id(input.account_id)


class DeleteAccountUseCase:
    @inject
    def __init__(self, repository: IAccountRepository, manager: MT5WorkerManager) -> None:
        self._repository = repository
        self._manager = manager

    def execute(self, account_id: AccountId):
        ensure_account_is_editable(self._manager, account_id)
        self._repository.delete_by_id(account_id)


class StartMT5WorkerUseCase:
    @inject
    def __init__(
        self,
        repository: IAccountRepository,
        cipher: Fernet,
        manager: MT5WorkerManager,
    ) -> None:
        self._repository = repository
        self._cipher = cipher
        self._manager = manager

    def execute(self, account_id: AccountId) -> WorkerStatus:
        account = self._repository.get_by_id(account_id)
        password = self._cipher.decrypt(account.connection.encrypted_password).decode()
        return self._manager.start(
            account_id.value,
            {
                "path": account.connection.path,
                "login": account.connection.login,
                "password": password,
                "server": account.connection.server,
                "portable": account.portable,
            },
        )


class StopMT5WorkerUseCase:
    @inject
    def __init__(self, manager: MT5WorkerManager) -> None:
        self._manager = manager

    def execute(self, account_id: AccountId) -> WorkerStatus:
        return self._manager.stop(account_id.value)
