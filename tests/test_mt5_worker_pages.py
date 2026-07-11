from fastapi import FastAPI
from fastapi.testclient import TestClient

from blueOcean.metatrader.workers import WorkerStatus
from blueOcean.routes.pages import (
    get_list_accounts_usecase,
    get_mt5_worker_manager,
    get_start_mt5_worker_usecase,
    get_stop_mt5_worker_usecase,
    router,
)


class EmptyListAccounts:
    def execute(self):
        return []


class WorkerUseCaseStub:
    def __init__(self):
        self.account_id = None

    def execute(self, account_id):
        self.account_id = account_id
        return WorkerStatus("starting", 1234)


class WorkerManagerStub:
    def get_statuses(self):
        return {
            "account-1": WorkerStatus("error", 1234, "MT5 initialize failed"),
        }


def test_start_and_stop_routes_delegate_to_worker_usecases():
    app = FastAPI()
    start = WorkerUseCaseStub()
    stop = WorkerUseCaseStub()
    app.dependency_overrides[get_list_accounts_usecase] = lambda: EmptyListAccounts()
    app.dependency_overrides[get_start_mt5_worker_usecase] = lambda: start
    app.dependency_overrides[get_stop_mt5_worker_usecase] = lambda: stop
    app.include_router(router)
    client = TestClient(app)

    start_response = client.post("/accounts/account-1/start", follow_redirects=False)
    stop_response = client.post("/accounts/account-1/stop", follow_redirects=False)

    assert start_response.status_code == 303
    assert stop_response.status_code == 303
    assert start.account_id.value == "account-1"
    assert stop.account_id.value == "account-1"


def test_worker_status_endpoint_returns_failure_reason():
    app = FastAPI()
    app.dependency_overrides[get_mt5_worker_manager] = lambda: WorkerManagerStub()
    app.include_router(router)

    response = TestClient(app).get("/accounts/worker-statuses")

    assert response.status_code == 200
    assert response.json() == {
        "account-1": {
            "state": "error",
            "pid": 1234,
            "error": "MT5 initialize failed",
        }
    }
