from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Type

import backtrader as bt
import pandas as pd
import quantstats as qs

from blueOcean.field import service
from blueOcean.logging import logger
from blueOcean.ohlcv import (IOhlcvRepository, LocalDataFeed, OhlcvFetcher,
                             Timeframe)


class FetchOhlcvUsecase:
    def __init__(self, repository: IOhlcvRepository, fetcher: OhlcvFetcher):
        self.repository = repository
        self.fetcher = fetcher

    def call(self, source, symbol):
        latest_at = self.repository.get_latest_timestamp(source, symbol)

        for batch in self.fetcher.fetch_ohlcv(symbol, latest_at):
            self.repository.save(batch, source, symbol)


class BacktestUsecase:
    @dataclass(frozen=True)
    class Result:
        report_path: Path

    def __init__(
        self,
        repository: IOhlcvRepository,
        symbol: str,
        source: str,
        timeframe=Timeframe.ONE_MINUTE,
        start_at=datetime.min,
        end_at=datetime.max,
    ):
        self.feed = LocalDataFeed(
            repository=repository,
            symbol=symbol,
            source=source,
            ohlcv_timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
        )

    def call(
        self,
        strategy: Type[service.TStrategy],
        **strategy_args,
    ):
        runner = service.StrategyRunner()
        runner.add_analyzer(bt.analyzers.TimeReturn, "timereturn")
        result, cerebro = runner.run(strategy, self.feed, **strategy_args)

        timereturn = result.analyzers.timereturn.get_analysis()
        report_path = self._output_report(timereturn, strategy.__name__)

        return self.Result(report_path=report_path)

    def _output_report(self, returns, strategy_name: str) -> Path:
        returns = pd.Series(returns)

        out_dir = Path("./out")
        out_dir.mkdir(exist_ok=True)

        # TODO: レポートファイルの命名規則を考える
        filename = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path = out_dir / filename

        qs.reports.html(returns, output=str(path))
        return path
