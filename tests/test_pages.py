from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace
from blueOcean.metatrader.workers import WorkerStatus

from blueOcean.routes.pages import (
    get_create_account_usecase,
    get_account_usecase,
    get_list_accounts_usecase,
    get_mt5_worker_manager,
)
from blueOcean.routes.pages import router


class EmptyListAccountsUseCase:
    def execute(self):
        return []


class ListAccountsUseCaseStub:
    def __init__(self, accounts):
        self.accounts = accounts

    def execute(self):
        return self.accounts


class InvalidCreateAccountUseCase:
    def execute(self, input):
        raise ValueError("MT5端末には絶対ローカルパスを指定してください")


class GetAccountUseCaseStub:
    def execute(self, account_id):
        return SimpleNamespace(
            id=account_id,
            name="Demo",
            connection=SimpleNamespace(
                path=r"C:\MT5\terminal64.exe",
                login=12345678,
                server="Broker-Demo",
            ),
            portable=False,
        )


class ErrorWorkerManagerStub:
    def get_statuses(self):
        return {"account-1": WorkerStatus("error", None, "login failed")}

    def get_status(self, account_id):
        return WorkerStatus("error", None, "login failed")


class RunningWorkerManagerStub:
    def get_statuses(self):
        return {"account-1": WorkerStatus("running", 1234)}

    def get_status(self, account_id):
        return WorkerStatus("running", 1234)


def test_create_error_is_rendered_in_dialog():
    app = FastAPI()
    app.dependency_overrides[get_list_accounts_usecase] = lambda: EmptyListAccountsUseCase()
    app.dependency_overrides[get_create_account_usecase] = lambda: InvalidCreateAccountUseCase()
    app.include_router(router)

    response = TestClient(app).post(
        "/accounts",
        data={
            "name": "Demo",
            "path": "relative/terminal64.exe",
            "login": "12345678",
            "password": "secret",
            "server": "Broker-Demo",
        },
    )

    assert response.status_code == 422
    assert "絶対ローカルパス" in response.text
    assert 'action="/accounts"' in response.text


def test_accounts_page_shows_add_link_without_registration_form():
    app = FastAPI()
    app.dependency_overrides[get_list_accounts_usecase] = lambda: EmptyListAccountsUseCase()
    app.include_router(router)

    response = TestClient(app).get("/accounts")

    assert response.status_code == 200
    assert 'href="/accounts/new"' in response.text
    assert 'name="path"' not in response.text


def test_new_account_page_uses_native_terminal_picker():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/accounts/new")

    assert response.status_code == 200
    assert 'name="path" required readonly' in response.text
    assert "data-mt5-path-picker" in response.text
    assert 'fetch("/dialogs/mt5-terminal")' in response.text


def test_account_edit_page_uses_account_specific_url():
    app = FastAPI()
    app.dependency_overrides[get_account_usecase] = lambda: GetAccountUseCaseStub()
    app.include_router(router)

    response = TestClient(app).get("/accounts/account-1")

    assert response.status_code == 200
    assert 'action="/accounts/account-1"' in response.text
    assert 'value="Demo"' in response.text


def test_error_account_offers_retry_instead_of_stop():
    account = GetAccountUseCaseStub().execute(SimpleNamespace(value="account-1"))
    app = FastAPI()
    app.dependency_overrides[get_list_accounts_usecase] = lambda: ListAccountsUseCaseStub([account])
    app.dependency_overrides[get_mt5_worker_manager] = lambda: ErrorWorkerManagerStub()
    app.include_router(router)

    response = TestClient(app).get("/accounts")

    assert response.status_code == 200
    assert ">再試行<" in response.text
    assert ">MT5を停止<" not in response.text


def test_running_account_disables_editing_on_list_and_edit_page():
    account = GetAccountUseCaseStub().execute(SimpleNamespace(value="account-1"))
    app = FastAPI()
    app.dependency_overrides[get_list_accounts_usecase] = lambda: ListAccountsUseCaseStub([account])
    app.dependency_overrides[get_account_usecase] = lambda: GetAccountUseCaseStub()
    app.dependency_overrides[get_mt5_worker_manager] = lambda: RunningWorkerManagerStub()
    app.include_router(router)
    client = TestClient(app)

    list_response = client.get("/accounts")
    edit_response = client.get("/accounts/account-1")

    assert 'title="MT5停止後に変更できます"' in list_response.text
    assert 'href="/accounts/account-1"' not in list_response.text
    assert edit_response.status_code == 200
    assert "先にMT5を停止してください" in edit_response.text
    assert "変更を保存" not in edit_response.text


def test_mt5_terminal_dialog_returns_selected_path(monkeypatch):
    monkeypatch.setattr(
        "blueOcean.routes.pages.select_mt5_terminal_path",
        lambda: r"C:\Program Files\MetaTrader 5\terminal64.exe",
    )
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/dialogs/mt5-terminal")

    assert response.status_code == 200
    assert response.json() == {"path": r"C:\Program Files\MetaTrader 5\terminal64.exe"}
