from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from blueOcean.container import get_injector
from blueOcean.strategy.models import StrategyConfig, StrategyAlreadyRunningError
from blueOcean.strategy.definitions import STRATEGY_DEFINITIONS, get_strategy_definition
from blueOcean.strategy.repositories import StrategyRepository, StrategyRunRepository
from blueOcean.strategy.supervisor import StrategySupervisor
from blueOcean.usecases import ListAccountsUseCase

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parents[2] / "templates")


def get_strategies() -> StrategyRepository:
    return get_injector().get(StrategyRepository)


def get_runs() -> StrategyRunRepository:
    return get_injector().get(StrategyRunRepository)


def get_supervisor() -> StrategySupervisor:
    return get_injector().get(StrategySupervisor)


def get_accounts() -> ListAccountsUseCase:
    return get_injector().get(ListAccountsUseCase)


@router.get("/strategies", response_class=HTMLResponse)
def strategies_page(
    request: Request,
    repository: Annotated[StrategyRepository, Depends(get_strategies)],
):
    return templates.TemplateResponse(request=request, name="strategies.html", context={"strategies": repository.list(), "definition_labels": {key: value.label for key, value in STRATEGY_DEFINITIONS.items()}})


@router.get("/strategies/new", response_class=HTMLResponse)
def strategy_new_page(
    request: Request,
    accounts: Annotated[ListAccountsUseCase, Depends(get_accounts)],
):
    return templates.TemplateResponse(request=request, name="strategy_form.html", context={"accounts": accounts.execute(), "definitions": STRATEGY_DEFINITIONS.values(), "error": None})


@router.post("/strategies")
async def strategy_create(
    request: Request,
    repository: Annotated[StrategyRepository, Depends(get_strategies)],
    accounts: Annotated[ListAccountsUseCase, Depends(get_accounts)],
    name: str = Form(...),
    definition_key: str = Form(...),
    account_id: str = Form(...),
    symbol: str = Form(...),
    timeframe: str = Form(...),
    mode: str = Form("paper"),
):
    try:
        submitted = await request.form()
        definition = get_strategy_definition(definition_key)
        parameters = {
            parameter.name: submitted.get(f"parameter_{definition.key}_{parameter.name}")
            for parameter in definition.parameters
        }
        repository.save(StrategyConfig(name=name, definition_key=definition_key, account_id=account_id, symbol=symbol, timeframe=timeframe, mode=mode, parameters=parameters))
    except ValueError as exc:
        return templates.TemplateResponse(request=request, name="strategy_form.html", context={"accounts": accounts.execute(), "definitions": STRATEGY_DEFINITIONS.values(), "error": str(exc)}, status_code=422)
    return RedirectResponse("/strategies", status_code=303)


@router.get("/runs", response_class=HTMLResponse)
def runs_page(
    request: Request,
    runs: Annotated[StrategyRunRepository, Depends(get_runs)],
    strategies: Annotated[StrategyRepository, Depends(get_strategies)],
):
    names = {item.id: item.name for item in strategies.list()}
    return templates.TemplateResponse(request=request, name="runs.html", context={"runs": runs.list(), "strategy_names": names})


@router.post("/strategies/{strategy_id}/runs")
def run_start(
    strategy_id: str,
    supervisor: Annotated[StrategySupervisor, Depends(get_supervisor)],
):
    try:
        supervisor.start(strategy_id)
    except StrategyAlreadyRunningError:
        pass
    return RedirectResponse("/runs", status_code=303)


@router.post("/runs/{run_id}/stop")
def run_stop(
    run_id: str,
    supervisor: Annotated[StrategySupervisor, Depends(get_supervisor)],
):
    supervisor.stop(run_id)
    return RedirectResponse("/runs", status_code=303)
