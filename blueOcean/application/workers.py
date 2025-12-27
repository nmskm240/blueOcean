import signal
import threading
import time
from abc import ABCMeta, abstractmethod
from datetime import UTC, datetime, timedelta
from multiprocessing import Process
from pathlib import Path
from queue import Queue

import backtrader as bt
import pandas as pd
import psutil
import quantstats as qs
from injector import Injector

from blueOcean.application.di import BacktestRuntimeModule, LiveTradeRuntimeModule
from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.domain.bot import BacktestContext, BotId, IBotWorker, LiveContext
from blueOcean.domain.ohlcv import OhlcvFetcher


class BotProcessWorker(Process, IBotWorker, metaclass=ABCMeta):
    def __init__(self):
        super().__init__()
        self._run_directory: Path | None = None

    def launch(self):
        self.start()

    def run(self):
        signal.signal(signal.SIGTERM, self._on_handle_sigterm)

        try:
            self._run()
        finally:
            self._create_report()

    @abstractmethod
    def _run(self) -> None:
        raise NotImplementedError()

    def _on_handle_sigterm(self, signum, frame):
        self._on_sigterm()
        raise SystemExit()

    def _on_sigterm(self) -> None:
        pass

    def _create_report(self) -> None:
        df = pd.read_csv(self._run_directory / "metrics.csv")
        if df.empty:
            return

        required_cols = {"timestamp", "analyzer", "value"}
        if not required_cols.issubset(df.columns):
            return

        df = df[df["analyzer"] == "timereturn"].copy()
        if df.empty:
            return

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        returns = pd.Series(df["value"].values, index=df["timestamp"])

        output_path = self._run_directory / "quantstats_report.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        qs.reports.html(returns, output=str(output_path))


class LiveTradeWorker(BotProcessWorker):
    def __init__(self, id: BotId, context: LiveContext):
        super().__init__()
        self._id = id
        self._context = context

        self.threads = []
        self.should_terminate = False

    def _run(self):
        container = Injector([LiveTradeRuntimeModule(self._id, self._context)])
        self._run_directory = container.get(Path)

        fetcher_factory = container.get(IOhlcvFetcherFactory)
        fetcher = fetcher_factory.create(self._context.account_id)
        queue = container.get(Queue)
        self.threads = [
            threading.Thread(
                name="fetcher",
                target=self._fetch_ohlcv,
                args=[fetcher, self._context.symbol, queue],
                daemon=True,
            ),
        ]
        for t in self.threads:
            t.start()

        cerebro = container.get(bt.Cerebro)
        cerebro.run(runonce=False)

    def shutdown(self):
        self.should_terminate = True
        for t in self.threads:
            t.join()

        super().terminate()

    def _fetch_ohlcv(self, fetcher: OhlcvFetcher, symbol: str, queue: Queue):
        while not self.should_terminate:
            now = datetime.now(tz=UTC)
            next_min = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            # MEMO: since_atの時間が含まれないことを考慮するため2分前の時間でリクエストを行う
            since_at = next_min - timedelta(minutes=2)
            sleep_time = (next_min - now).total_seconds()
            time.sleep(sleep_time)

            for batch in fetcher.fetch_ohlcv(symbol, since_at=since_at):
                for ohlcv in batch:
                    if now < ohlcv.time:
                        continue
                    queue.put_nowait(ohlcv)
                    break

    def _on_sigterm(self) -> None:
        self.should_terminate = True


class BacktestWorker(BotProcessWorker):
    def __init__(self, id: BotId, context: BacktestContext):
        super().__init__()
        self._id = id
        self._context = context

    def _run(self):
        container = Injector([BacktestRuntimeModule(self._id, self._context)])
        self._run_directory = container.get(Path)

        cerebro = container.get(bt.Cerebro)
        cerebro.run(runonce=False)

    def shutdown(self):
        super().terminate()


class RecoverWorker(IBotWorker):
    """起動済みプロセスへの再接続用Worker"""

    def __init__(self, pid):
        self._process = psutil.Process(pid)

    def launch(self):
        raise RuntimeError(f"{self.__class__.__name__} cannot be started")

    def shutdown(self):
        self._process.terminate()
