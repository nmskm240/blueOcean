from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import Fernet
from injector import inject

from blueOcean.models import Account, AccountId, IAccountRepository, Mt5Connection


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


class UpdateAccountUseCase:
    @inject
    def __init__(self, repository: IAccountRepository, cipher: Fernet) -> None:
        self._repository = repository
        self._cipher = cipher

    def execute(self, input: UpdateAccountInput) -> Account:
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
    def __init__(self, repository: IAccountRepository) -> None:
        self._repository = repository

    def execute(self, id: AccountId):
        self._repository.delete_by_id(id)
