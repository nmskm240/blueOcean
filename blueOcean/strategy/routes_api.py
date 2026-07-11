from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from blueOcean.container import get_injector
from blueOcean.strategy.models import (
    StrategyConfig,
    StrategyAlreadyRunningError,
    StrategyNotFoundError,
    StrategyRunNotFoundError,
)
from blueOcean.strategy.registry import STRATEGY_DEFINITIONS
from blueOcean.strategy.repositories import StrategyRepository, StrategyRunRepository
from blueOcean.strategy.supervisor import StrategySupervisor

router = APIRouter(prefix="/api", tags=["Strategies"])


def get_strategies() -> StrategyRepository:
    return get_injector().get(StrategyRepository)


def get_runs() -> StrategyRunRepository:
    return get_injector().get(StrategyRunRepository)


def get_supervisor() -> StrategySupervisor:
    return get_injector().get(StrategySupervisor)


class StrategyInput(BaseModel):
    name: str
    definition_key: str
    account_id: str
    symbol: str
    timeframe: str
    mode: str = "paper"
    parameters: dict = Field(default_factory=dict)


class StrategyOutput(StrategyInput):
    id: str


class RunCreate(BaseModel):
    strategy_id: str


class RunOutput(BaseModel):
    id: str
    strategy_id: str
    state: str
    pid: int | None
    error: str | None
    started_at: datetime
    heartbeat_at: datetime | None
    stopped_at: datetime | None


@router.get("/strategy-definitions")
def list_strategy_definitions():
    return [
        {
            "key": definition.key,
            "label": definition.label,
            "parameters": [
                {
                    "name": parameter.name,
                    "label": parameter.label,
                    "type": parameter.value_type.__name__,
                    "default": parameter.default,
                    "minimum": parameter.minimum,
                }
                for parameter in definition.parameters
            ],
        }
        for definition in STRATEGY_DEFINITIONS.values()
    ]


@router.get("/strategies", response_model=list[StrategyOutput])
def list_strategies(repository: Annotated[StrategyRepository, Depends(get_strategies)]):
    return repository.list()


@router.post("/strategies", response_model=StrategyOutput, status_code=201)
def create_strategy(
    payload: StrategyInput,
    repository: Annotated[StrategyRepository, Depends(get_strategies)],
):
    try:
        return repository.save(StrategyConfig(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/strategies/{strategy_id}", response_model=StrategyOutput)
def get_strategy(
    strategy_id: str,
    repository: Annotated[StrategyRepository, Depends(get_strategies)],
):
    try:
        return repository.get(strategy_id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")


@router.get("/runs", response_model=list[RunOutput])
def list_runs(repository: Annotated[StrategyRunRepository, Depends(get_runs)]):
    return repository.list()


@router.post("/runs", response_model=RunOutput, status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: RunCreate,
    supervisor: Annotated[StrategySupervisor, Depends(get_supervisor)],
):
    try:
        return supervisor.start(payload.strategy_id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except StrategyAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/runs/{run_id}", response_model=RunOutput)
def get_run(run_id: str, repository: Annotated[StrategyRunRepository, Depends(get_runs)]):
    try:
        return repository.get(run_id)
    except StrategyRunNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy run not found")


@router.post("/runs/{run_id}/stop", response_model=RunOutput)
def stop_run(
    run_id: str,
    supervisor: Annotated[StrategySupervisor, Depends(get_supervisor)],
):
    try:
        return supervisor.stop(run_id)
    except StrategyRunNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy run not found")
