from fastapi import FastAPI
from fastapi.testclient import TestClient

from blueOcean.models import Account, AccountId, AccountNotFoundError, Mt5Connection
from blueOcean.routes.api import (
    get_create_account_usecase,
    get_delete_account_usecase,
    get_account_usecase,
    get_list_accounts_usecase,
    get_mt5_worker_manager,
    get_start_mt5_worker_usecase,
    get_stop_mt5_worker_usecase,
    get_update_account_usecase,
    router,
)
from blueOcean.usecases import AccountWorkerActiveError
from blueOcean.metatrader.workers import WorkerStatus


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


class GetAccountUseCaseStub:
    def __init__(self, account=None):
        self.account = account

    def execute(self, account_id):
        if self.account is None:
            raise AccountNotFoundError
        return self.account


class WorkerUseCaseStub:
    def __init__(self, status):
        self.status = status
        self.account_id = None

    def execute(self, account_id):
        self.account_id = account_id
        return self.status


class WorkerManagerStub:
    def get_status(self, account_id):
        return WorkerStatus("error", 321, "login failed")


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
    def __init__(self, *, not_found=False, error=None):
        self.not_found = not_found
        self.error = error
        self.deleted_id = None

    def execute(self, account_id):
        self.deleted_id = account_id
        if self.not_found:
            raise AccountNotFoundError
        if self.error:
            raise self.error


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


def test_get_account_returns_one_account():
    client = make_client({get_account_usecase: lambda: GetAccountUseCaseStub(make_account())})

    response = client.get("/api/accounts/account-1")

    assert response.status_code == 200
    assert response.json()["id"] == "account-1"
    assert "encrypted-secret" not in response.text


def test_get_account_returns_404_for_missing_account():
    client = make_client({get_account_usecase: lambda: GetAccountUseCaseStub()})

    response = client.get("/api/accounts/missing")

    assert response.status_code == 404


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


def test_update_account_returns_409_while_worker_is_active():
    usecase = UpdateAccountUseCaseStub(
        error=AccountWorkerActiveError("MT5がrunningの間はアカウント設定を変更できません")
    )
    client = make_client({get_update_account_usecase: lambda: usecase})

    response = client.put(
        "/api/accounts/account-1",
        json={
            "name": "Demo",
            "path": r"C:\MT5\terminal64.exe",
            "login": 12345678,
            "server": "Broker-Demo",
        },
    )

    assert response.status_code == 409


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


def test_delete_account_returns_409_while_worker_is_active():
    client = make_client(
        {
            get_delete_account_usecase: lambda: DeleteAccountUseCaseStub(
                error=AccountWorkerActiveError("MT5がstartingの間はアカウント設定を変更できません")
            )
        }
    )

    response = client.delete("/api/accounts/account-1")

    assert response.status_code == 409


def test_worker_status_and_commands_are_available_via_api():
    account = make_account()
    start = WorkerUseCaseStub(WorkerStatus("starting", 123))
    stop = WorkerUseCaseStub(WorkerStatus("stopped"))
    client = make_client(
        {
            get_account_usecase: lambda: GetAccountUseCaseStub(account),
            get_mt5_worker_manager: lambda: WorkerManagerStub(),
            get_start_mt5_worker_usecase: lambda: start,
            get_stop_mt5_worker_usecase: lambda: stop,
        }
    )

    status_response = client.get("/api/accounts/account-1/worker")
    start_response = client.post("/api/accounts/account-1/worker/start")
    stop_response = client.post("/api/accounts/account-1/worker/stop")

    assert status_response.json() == {"state": "error", "pid": 321, "error": "login failed"}
    assert start_response.status_code == 202
    assert start_response.json()["state"] == "starting"
    assert stop_response.status_code == 200
    assert stop_response.json()["state"] == "stopped"
    assert start.account_id == AccountId("account-1")
    assert stop.account_id == AccountId("account-1")
