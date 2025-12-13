from __future__ import annotations

from pathlib import Path

import pandas as pd
import quantstats as qs
from injector import Injector

from blueOcean.application.di import BacktestModule, FetcherModule, RealTradeModule
from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.application.services import WorkerService
from blueOcean.domain.ohlcv import IOhlcvRepository, OhlcvFetcher


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
