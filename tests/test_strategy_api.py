from fastapi import FastAPI
from fastapi.testclient import TestClient

from blueOcean.strategy.models import StrategyRun
from blueOcean.strategy.dependencies import get_strategy_service
from blueOcean.strategy.routes_api import router
from blueOcean.strategy.services import StrategyService


class StrategyRepositoryStub:
    def __init__(self):
        self.items = {}

    def list(self):
        return list(self.items.values())

    def save(self, strategy):
        self.items[strategy.id] = strategy
        return strategy

    def get(self, strategy_id):
        return self.items[strategy_id]


class RunRepositoryStub:
    def __init__(self):
        self.items = {}

    def list(self):
        return list(self.items.values())

    def get(self, run_id):
        return self.items[run_id]


class SupervisorStub:
    def __init__(self, runs):
        self.runs = runs

    def start(self, strategy_id):
        run = StrategyRun(strategy_id=strategy_id, pid=1234)
        self.runs.items[run.id] = run
        return run

    def stop(self, run_id):
        current = self.runs.items[run_id]
        stopped = StrategyRun(
            id=current.id,
            strategy_id=current.strategy_id,
            state="stopped",
            started_at=current.started_at,
        )
        self.runs.items[run_id] = stopped
        return stopped


def make_client():
    strategies = StrategyRepositoryStub()
    runs = RunRepositoryStub()
    supervisor = SupervisorStub(runs)
    service = StrategyService(strategies, runs, supervisor)
    app = FastAPI()
    app.dependency_overrides[get_strategy_service] = lambda: service
    app.include_router(router)
    return TestClient(app), strategies, runs


def test_strategy_and_run_api_flow():
    client, strategies, runs = make_client()

    created = client.post(
        "/api/strategies",
        json={
            "name": "Dummy EURUSD",
            "definition_key": "moving_average_cross",
            "account_id": "account-1",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data_source": "synthetic",
            "execution_backend": "paper",
            "parameters": {"fast_period": 20, "slow_period": 50},
        },
    )
    strategy_id = created.json()["id"]
    started = client.post("/api/runs", json={"strategy_id": strategy_id})
    run_id = started.json()["id"]
    stopped = client.post(f"/api/runs/{run_id}/stop")

    assert created.status_code == 201
    assert strategies.items[strategy_id].symbol == "EURUSD"
    assert strategies.items[strategy_id].parameters == {"fast_period": 20, "slow_period": 50}
    assert started.status_code == 202
    assert started.json()["state"] == "starting"
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "stopped"
    assert runs.items[run_id].state == "stopped"


def test_strategy_rejects_invalid_mode():
    client, _, _ = make_client()

    response = client.post(
        "/api/strategies",
        json={
            "name": "Invalid",
            "definition_key": "dummy_heartbeat",
            "account_id": "account-1",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data_source": "yfinance",
            "execution_backend": "paper",
        },
    )

    assert response.status_code == 422


def test_strategy_definitions_describe_typed_parameters():
    client, _, _ = make_client()

    response = client.get("/api/strategy-definitions")

    assert response.status_code == 200
    moving_average = next(item for item in response.json() if item["key"] == "moving_average_cross")
    assert [item["name"] for item in moving_average["parameters"]] == [
        "fast_period",
        "slow_period",
    ]


def test_yfinance_backtest_does_not_require_mt5_account():
    client, strategies, _ = make_client()

    response = client.post(
        "/api/strategies",
        json={
            "name": "Independent backtest",
            "definition_key": "dummy_heartbeat",
            "symbol": "AAPL",
            "timeframe": "D1",
            "data_source": "yfinance",
            "execution_backend": "backtest",
        },
    )

    assert response.status_code == 201
    assert strategies.items[response.json()["id"]].account_id is None
