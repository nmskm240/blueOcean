from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from blueOcean.container import get_injector
from blueOcean.strategy.dependencies import get_strategy_service
from blueOcean.strategy.models import StrategyAlreadyRunningError
from blueOcean.strategy.registry import get_strategy_definition
from blueOcean.strategy.services import CreateStrategyConfig, StrategyService
from blueOcean.usecases import ListAccountsUseCase

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parents[2] / "templates")


def get_accounts() -> ListAccountsUseCase:
    return get_injector().get(ListAccountsUseCase)


def render_strategy_form(
    request: Request,
    service: StrategyService,
    accounts: ListAccountsUseCase,
    *,
    error: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="strategy_form.html",
        context={
            "accounts": accounts.execute(),
            "definitions": service.definitions(),
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/strategies", response_class=HTMLResponse)
def strategies_page(
    request: Request,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    return templates.TemplateResponse(
        request=request,
        name="strategies.html",
        context={
            "strategies": service.list_strategies(),
            "definition_labels": {
                definition.key: definition.label
                for definition in service.definitions()
            },
        },
    )


@router.get("/strategies/new", response_class=HTMLResponse)
def strategy_new_page(
    request: Request,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
    accounts: Annotated[ListAccountsUseCase, Depends(get_accounts)],
):
    return render_strategy_form(request, service, accounts)


@router.post("/strategies")
async def strategy_create(
    request: Request,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
    accounts: Annotated[ListAccountsUseCase, Depends(get_accounts)],
    name: str = Form(...),
    definition_key: str = Form(...),
    account_id: str = Form(""),
    symbol: str = Form(...),
    timeframe: str = Form(...),
    data_source: str = Form("synthetic"),
    execution_backend: str = Form("paper"),
    history_period: str = Form("1y"),
    initial_cash: float = Form(100_000.0),
    commission: float = Form(0.001),
):
    try:
        submitted = await request.form()
        definition = get_strategy_definition(definition_key)
        parameters = {
            parameter.name: submitted.get(
                f"parameter_{definition.key}_{parameter.name}"
            )
            for parameter in definition.parameters
        }
        service.create_strategy(
            CreateStrategyConfig(
                name=name,
                definition_key=definition_key,
                account_id=account_id or None,
                symbol=symbol,
                timeframe=timeframe,
                data_source=data_source,
                execution_backend=execution_backend,
                history_period=history_period,
                initial_cash=initial_cash,
                commission=commission,
                parameters=parameters,
            )
        )
    except ValueError as exc:
        return render_strategy_form(
            request,
            service,
            accounts,
            error=str(exc),
            status_code=422,
        )
    return RedirectResponse("/strategies", status_code=303)


@router.get("/runs", response_class=HTMLResponse)
def runs_page(
    request: Request,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    names = {item.id: item.name for item in service.list_strategies()}
    return templates.TemplateResponse(
        request=request,
        name="runs.html",
        context={"runs": service.list_runs(), "strategy_names": names},
    )


@router.post("/strategies/{strategy_id}/runs")
def run_start(
    strategy_id: str,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    try:
        service.start_run(strategy_id)
    except StrategyAlreadyRunningError:
        pass
    return RedirectResponse("/runs", status_code=303)


@router.post("/runs/{run_id}/stop")
def run_stop(
    run_id: str,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
):
    service.stop_run(run_id)
    return RedirectResponse("/runs", status_code=303)
