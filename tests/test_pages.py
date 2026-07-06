from fastapi import FastAPI
from fastapi.testclient import TestClient

from blueOcean.routes.pages import (
    get_create_account_usecase,
    get_list_accounts_usecase,
)
from blueOcean.routes.pages import router


class EmptyListAccountsUseCase:
    def execute(self):
        return []


class InvalidCreateAccountUseCase:
    def execute(self, input):
        raise ValueError("MT5端末には絶対ローカルパスを指定してください")


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
    assert "保存できませんでした" in response.text
    assert "絶対ローカルパス" in response.text
    assert 'class="modal" open' in response.text
    assert 'method="dialog"' in response.text
