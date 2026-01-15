from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from blueOcean.domain.bot import BotId
from blueOcean.domain.ohlcv import Timeframe
from blueOcean.presentation.reporting import build_report
from blueOcean.presentation.scopes import (
    AppScope,
    BacktestDialogScope,
    BotDetailPageScope,
    BotTopPageScope,
    OhlcvFetchDialogScope,
)
from blueOcean.shared.registries import StrategyRegistry

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI()
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.app_scope = AppScope()

    def nav_items(current: str) -> list[dict[str, Any]]:
        items = [
            {"label": "Home", "href": "/"},
            {"label": "Bots", "href": "/bots"},
            {"label": "Strategies", "href": "/strategies"},
        ]
        for item in items:
            item["active"] = item["href"] == current
        return items

    def base_context(request: Request, title: str) -> dict[str, Any]:
        return {
            "request": request,
            "title": title,
            "nav_items": nav_items(request.url.path),
        }

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        context = base_context(request, "Home")
        return templates.TemplateResponse("pages/home.html", context)

    @app.get("/bots", response_class=HTMLResponse)
    def bots(request: Request):
        scope = BotTopPageScope(request.app.state.app_scope)
        state = scope.notifier.state
        context = base_context(request, "Bots")
        context["bots"] = state.bots
        return templates.TemplateResponse("pages/bots.html", context)

    @app.get("/bots/{bot_id}", response_class=HTMLResponse)
    def bot_detail(request: Request, bot_id: str):
        try:
            scope = BotDetailPageScope(request.app.state.app_scope, BotId(bot_id))
            state = scope.notifier.state
            bot = state.info
            report = build_report(state.time_returns)
            error = None
        except Exception as exc:
            bot = None
            report = None
            error = str(exc)
        context = base_context(request, "Bot Detail")
        context.update(
            {
                "bot": bot,
                "report": report,
                "error": error,
            }
        )
        return templates.TemplateResponse("pages/bot_detail.html", context)

    @app.get("/strategies", response_class=HTMLResponse)
    def strategies(request: Request):
        strategies_list = [name for name, _ in StrategyRegistry]
        context = base_context(request, "Strategies")
        context["strategies"] = strategies_list
        return templates.TemplateResponse("pages/strategies.html", context)

    @app.get("/htmx/close-modal", response_class=HTMLResponse)
    def close_modal():
        return ""

    @app.get("/htmx/ohlcv", response_class=HTMLResponse)
    def ohlcv_dialog(request: Request):
        scope = OhlcvFetchDialogScope(request.app.state.app_scope)
        state = scope.notifier.state
        context = {
            "request": request,
            "exchanges": state.exchanges,
        }
        return templates.TemplateResponse("partials/ohlcv_modal.html", context)

    @app.post("/htmx/ohlcv", response_class=HTMLResponse)
    def ohlcv_submit(
        request: Request,
        exchange: str = Form(""),
        symbol: str = Form(""),
    ):
        scope = OhlcvFetchDialogScope(request.app.state.app_scope)
        notifier = scope.notifier
        state = notifier.state
        notifier.update(exchange=exchange, symbol=symbol)
        notifier.submit()
        context = {
            "request": request,
            "exchanges": state.exchanges,
            "message": "Saved price data request.",
        }
        return templates.TemplateResponse("partials/ohlcv_modal.html", context)

    @app.get("/htmx/backtest", response_class=HTMLResponse)
    def backtest_dialog(request: Request):
        scope = BacktestDialogScope(request.app.state.app_scope)
        context = {
            "request": request,
            "exchanges": scope.exchange_symbol_accessor.exchanges,
            "timeframes": [e.name for e in Timeframe],
            "strategies": [name for name, _ in StrategyRegistry],
        }
        return templates.TemplateResponse("partials/backtest_modal.html", context)

    @app.get("/htmx/exchange-symbols", response_class=HTMLResponse)
    def exchange_symbols(request: Request, exchange: str | None = None):
        scope = BacktestDialogScope(request.app.state.app_scope)
        if exchange:
            try:
                symbols = scope.exchange_symbol_accessor.symbols_for(exchange)
            except FileNotFoundError:
                symbols = []
        else:
            symbols = []
        context = {
            "request": request,
            "symbols": symbols,
        }
        return templates.TemplateResponse("partials/symbol_options.html", context)

    @app.get("/htmx/strategy-params", response_class=HTMLResponse)
    def strategy_params(request: Request, strategy: str | None = None):
        params: list[dict[str, Any]] = []
        if strategy:
            params = [_param_context(name, default) for name, default in StrategyRegistry.params_of(strategy)]
        context = {
            "request": request,
            "params": params,
        }
        return templates.TemplateResponse("partials/strategy_params.html", context)

    @app.post("/htmx/backtest", response_class=HTMLResponse)
    async def backtest_submit(
        request: Request,
        exchange: str = Form(""),
        symbol: str = Form(""),
        timeframe: str = Form(Timeframe.ONE_MINUTE.name),
        strategy: str | None = Form(None),
        start_date: str | None = Form(None),
        end_date: str | None = Form(None),
    ):
        scope = BacktestDialogScope(request.app.state.app_scope)
        notifier = scope.notifier
        form = await request.form()
        params = _parse_strategy_args(form, strategy)
        notifier.update(
            source=exchange,
            symbol=symbol,
            timeframe=_parse_timeframe(timeframe),
            strategy=strategy,
            strategy_args=params,
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        )
        notifier.on_request_backtest()

        bot_scope = BotTopPageScope(request.app.state.app_scope)
        bots = bot_scope.notifier.state.bots
        context = {
            "request": request,
            "exchanges": scope.exchange_symbol_accessor.exchanges,
            "timeframes": [e.name for e in Timeframe],
            "strategies": [name for name, _ in StrategyRegistry],
            "message": "Backtest started.",
            "bots": bots,
        }
        return templates.TemplateResponse("partials/backtest_modal.html", context)

    return app


def _parse_date(value: str | None) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _parse_timeframe(value: str) -> Timeframe:
    try:
        return Timeframe[value]
    except KeyError:
        return Timeframe.ONE_MINUTE


def _parse_strategy_args(form: Any, strategy: str | None) -> dict[str, Any]:
    if not strategy:
        return {}
    params = StrategyRegistry.params_of(strategy)
    data = {}
    if not form:
        return {}
    for name, default in params:
        key = f"strategy_arg__{name}"
        raw = form.get(key)
        if raw is None:
            data[name] = default
            continue
        data[name] = _parse_value(raw, default)
    return data


def _parse_value(raw: Any, default: Any) -> Any:
    if isinstance(default, bool):
        return str(raw).lower() in {"1", "true", "on", "yes"}
    if isinstance(default, int):
        try:
            return int(raw)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(raw)
        except ValueError:
            return default
    return raw


def _param_context(name: str, default: Any) -> dict[str, Any]:
    if isinstance(default, bool):
        kind = "checkbox"
    elif isinstance(default, int):
        kind = "number"
    elif isinstance(default, float):
        kind = "float"
    else:
        kind = "text"
    return {
        "name": name,
        "value": default,
        "kind": kind,
    }
