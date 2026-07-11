from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from blueOcean.strategy.dependencies import get_strategy_service
from blueOcean.strategy.models import (
    StrategyAlreadyRunningError,
    StrategyNotFoundError,
    StrategyRunNotFoundError,
)
from blueOcean.strategy.services import CreateStrategyConfig, StrategyService

router = APIRouter(prefix="/api", tags=["Strategies"])


class StrategyInput(BaseModel):
    name: str
    definition_key: str
    account_id: str | None = None
    symbol: str
    timeframe: str
    data_source: str = "synthetic"
    execution_backend: str = "paper"
    history_period: str = "1y"
    initial_cash: float = 100_000.0
    commission: float = 0.001
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
    result: dict | None


@router.get("/strategy-definitions")
def list_strategy_definitions(
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
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
        for definition in service.definitions()
    ]


@router.get("/strategies", response_model=list[StrategyOutput])
def list_strategies(
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    return service.list_strategies()


@router.post("/strategies", response_model=StrategyOutput, status_code=201)
def create_strategy(
    payload: StrategyInput,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    try:
        return service.create_strategy(CreateStrategyConfig(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/strategies/{strategy_id}", response_model=StrategyOutput)
def get_strategy(
    strategy_id: str,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    try:
        return service.get_strategy(strategy_id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")


@router.get("/runs", response_model=list[RunOutput])
def list_runs(service: Annotated[StrategyService, Depends(get_strategy_service)]):
    return service.list_runs()


@router.post("/runs", response_model=RunOutput, status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: RunCreate,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    try:
        return service.start_run(payload.strategy_id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except StrategyAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/runs/{run_id}", response_model=RunOutput)
def get_run(
    run_id: str,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    try:
        return service.get_run(run_id)
    except StrategyRunNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy run not found")


@router.post("/runs/{run_id}/stop", response_model=RunOutput)
def stop_run(
    run_id: str,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    try:
        return service.stop_run(run_id)
    except StrategyRunNotFoundError:
        raise HTTPException(status_code=404, detail="Strategy run not found")
