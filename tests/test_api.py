from fastapi import FastAPI
from fastapi.testclient import TestClient

from blueOcean.models import Account, AccountId, AccountNotFoundError, Mt5Connection
from blueOcean.routes.api import (
    get_create_account_usecase,
    get_delete_account_usecase,
    get_list_accounts_usecase,
    get_update_account_usecase,
    router,
)


def make_account(
    *,
    id: str = "account-1",
    name: str = "Demo",
    path: str = r"C:\MT5\terminal64.exe",
    login: int = 12345678,
    server: str = "Broker-Demo",
    portable: bool = False,
) -> Account:
    return Account(
        id=AccountId(id),
        name=name,
        connection=Mt5Connection(path, server, login, b"encrypted-secret"),
        portable=portable,
    )


class ListAccountsUseCaseStub:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self):
        return self.accounts


class CreateAccountUseCaseStub:
    def __init__(self, account, *, error=None):
        self.account = account
        self.error = error
        self.input = None

    def execute(self, input):
        self.input = input
        if self.error:
            raise self.error
        return self.account


class UpdateAccountUseCaseStub:
    def __init__(self, account=None, *, not_found=False, error=None):
        self.account = account
        self.not_found = not_found
        self.error = error
        self.input = None

    def execute(self, input):
        self.input = input
        if self.not_found:
            raise AccountNotFoundError
        if self.error:
            raise self.error
        return self.account


class DeleteAccountUseCaseStub:
    def __init__(self, *, not_found=False):
        self.not_found = not_found
        self.deleted_id = None

    def execute(self, account_id):
        self.deleted_id = account_id
        if self.not_found:
            raise AccountNotFoundError


def make_client(dependency_overrides) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides.update(dependency_overrides)
    return TestClient(app)


def test_list_accounts_returns_accounts_without_password_value():
    client = make_client(
        {
            get_list_accounts_usecase: lambda: ListAccountsUseCaseStub(
                [
                    make_account(),
                    make_account(
                        id="account-2",
                        name="Live",
                        login=87654321,
                        server="Broker-Live",
                        portable=True,
                    ),
                ]
            )
        }
    )

    response = client.get("/api/accounts")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "account-1",
            "name": "Demo",
            "path": r"C:\MT5\terminal64.exe",
            "login": 12345678,
            "server": "Broker-Demo",
            "portable": False,
            "has_password": True,
        },
        {
            "id": "account-2",
            "name": "Live",
            "path": r"C:\MT5\terminal64.exe",
            "login": 87654321,
            "server": "Broker-Live",
            "portable": True,
            "has_password": True,
        },
    ]
    assert "encrypted-secret" not in response.text


def test_create_account_passes_payload_to_usecase_and_returns_created_account():
    usecase = CreateAccountUseCaseStub(make_account(id="new-account", portable=True))
    client = make_client({get_create_account_usecase: lambda: usecase})

    response = client.post(
        "/api/accounts",
        json={
            "name": "Demo",
            "path": r"C:\MT5\terminal64.exe",
            "login": 12345678,
            "password": "plain-secret",
            "server": "Broker-Demo",
            "portable": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == "new-account"
    assert response.json()["has_password"] is True
    assert "plain-secret" not in response.text
    assert usecase.input.name == "Demo"
    assert usecase.input.path == r"C:\MT5\terminal64.exe"
    assert usecase.input.login == 12345678
    assert usecase.input.password == "plain-secret"
    assert usecase.input.server == "Broker-Demo"
    assert usecase.input.portable is True


def test_create_account_requires_password():
    client = make_client({get_create_account_usecase: lambda: CreateAccountUseCaseStub(None)})

    response = client.post(
        "/api/accounts",
        json={
            "name": "Demo",
            "path": r"C:\MT5\terminal64.exe",
            "login": 12345678,
            "server": "Broker-Demo",
        },
    )

    assert response.status_code == 422


def test_create_account_returns_422_when_path_is_invalid():
    usecase = CreateAccountUseCaseStub(
        None,
        error=ValueError("MT5端末には絶対ローカルパスを指定してください"),
    )
    client = make_client({get_create_account_usecase: lambda: usecase})

    response = client.post(
        "/api/accounts",
        json={
            "name": "Demo",
            "path": "relative/terminal64.exe",
            "login": 12345678,
            "password": "plain-secret",
            "server": "Broker-Demo",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "MT5端末には絶対ローカルパスを指定してください"}
    assert usecase.input.path == "relative/terminal64.exe"


def test_update_account_passes_none_password_when_omitted():
    usecase = UpdateAccountUseCaseStub(make_account(id="account-1", name="Updated"))
    client = make_client({get_update_account_usecase: lambda: usecase})

    response = client.put(
        "/api/accounts/account-1",
        json={
            "name": "Updated",
            "path": r"C:\MT5\terminal64.exe",
            "login": 12345678,
            "server": "Broker-Demo",
            "portable": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"
    assert usecase.input.account_id == AccountId("account-1")
    assert usecase.input.password is None


def test_update_account_returns_404_when_account_does_not_exist():
    client = make_client({get_update_account_usecase: lambda: UpdateAccountUseCaseStub(not_found=True)})

    response = client.put(
        "/api/accounts/missing-account",
        json={
            "name": "Missing",
            "path": r"C:\MT5\terminal64.exe",
            "login": 12345678,
            "server": "Broker-Demo",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_update_account_returns_422_when_path_is_invalid():
    usecase = UpdateAccountUseCaseStub(
        error=ValueError("MT5端末には絶対ローカルパスを指定してください"),
    )
    client = make_client({get_update_account_usecase: lambda: usecase})

    response = client.put(
        "/api/accounts/account-1",
        json={
            "name": "Demo",
            "path": "relative/terminal64.exe",
            "login": 12345678,
            "server": "Broker-Demo",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "MT5端末には絶対ローカルパスを指定してください"}
    assert usecase.input.account_id == AccountId("account-1")
    assert usecase.input.path == "relative/terminal64.exe"


def test_delete_account_passes_id_to_usecase_and_returns_no_content():
    usecase = DeleteAccountUseCaseStub()
    client = make_client({get_delete_account_usecase: lambda: usecase})

    response = client.delete("/api/accounts/account-1")

    assert response.status_code == 204
    assert response.content == b""
    assert usecase.deleted_id == AccountId("account-1")


def test_delete_account_returns_404_when_account_does_not_exist():
    client = make_client({get_delete_account_usecase: lambda: DeleteAccountUseCaseStub(not_found=True)})

    response = client.delete("/api/accounts/missing-account")

    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}
