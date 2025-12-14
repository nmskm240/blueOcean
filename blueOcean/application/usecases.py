from __future__ import annotations

from pathlib import Path

import pandas as pd
import quantstats as qs
from injector import Injector

from blueOcean.application.di import (
    AppDatabaseModule,
    BacktestModule,
    FetcherModule,
    RealTradeModule,
)
from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.application.services import WorkerService
from blueOcean.domain.account import Account, ApiCredential
from blueOcean.domain.ohlcv import IOhlcvRepository, OhlcvFetcher
from blueOcean.infra.database.repositories import AccountRepository


def fetch_ohlcv(source: str, symbol: str):
    container = Injector([FetcherModule])
    repository = container.get(IOhlcvRepository)
    fetcher = container.get(OhlcvFetcher)

    latest_at = repository.get_latest_timestamp(source, symbol)

    for batch in fetcher.fetch_ohlcv(symbol, latest_at):
        repository.save(batch, source, symbol)


def run_bot(config, bot_id: str | None = None):
    if isinstance(config, BacktestConfig):
        container = Injector([BacktestModule(config)])
        worker_service = container.get(WorkerService)
        worker = worker_service.spawn_backtest(config)
        return worker

    elif isinstance(config, BotConfig):
        if bot_id is None:
            raise ValueError("bot_id is required for real trade bot")
        container = Injector([RealTradeModule(config)])
        worker_service = container.get(WorkerService)
        worker = worker_service.spawn_real_trade(bot_id, config)
        return worker

    else:
        raise TypeError(f"Unsupported config: {type(config)}")


def export_report(returns: pd.Series, path: Path):
    qs.reports.html(returns, output=str(path))


def register_api_credential(
    exchange: str,
    api_key: str,
    api_secret: str,
    is_sandbox: bool,
    label: str,
) -> str:
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)

    account = Account(
        credential=ApiCredential(
            exchange=exchange,
            key=api_key,
            secret=api_secret,
            is_sandbox=is_sandbox,
        ),
        label=label,
    )

    return repository.create_account(account)


def list_api_credentials():
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)
    return repository.list()


def update_api_credential(
    account_id: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    is_sandbox: bool,
    label: str,
) -> None:
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)

    account = Account(
        credential=ApiCredential(
            exchange=exchange,
            key=api_key,
            secret=api_secret,
            is_sandbox=is_sandbox,
        ),
        label=label,
    )

    repository.update_account(account_id, account)


def delete_api_credential(account_id: str) -> None:
    container = Injector([AppDatabaseModule()])
    repository = container.get(AccountRepository)
    repository.delete_account(account_id)
