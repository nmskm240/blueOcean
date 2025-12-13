import threading
import time
from datetime import UTC, datetime, timedelta
from multiprocessing import Process
from queue import Queue

import backtrader as bt
from injector import Injector

from blueOcean.application.di import BacktestModule, RealTradeModule
from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.domain.ohlcv import OhlcvFetcher


class RealTradeWorker(Process):
    def __init__(self, config: BotConfig):
        super().__init__()
        self.config = config

        self.threads = []
        self.should_terminate = False

    def run(self):
        container = Injector([RealTradeModule(self.config)])

        fetcher = container.get(OhlcvFetcher)
        queue = container.get(Queue)
        self.threads = [
            threading.Thread(
                name="fetcher",
                target=self._fetch_ohlcv,
                args=[fetcher, self.config.symbol, queue],
                daemon=True,
            ),
        ]
        for t in self.threads:
            t.start()

        cerebro = container.get(bt.Cerebro)
        cerebro.run()

    def terminate(self):
        self.should_terminate = True
        for t in self.threads:
            t.join()

        return super().terminate()

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

class BacktestWorker(Process):
    def __init__(self, config:BacktestConfig):
        super().__init__()

        self.config = config

    def run(self):
        container = Injector([BacktestModule(self.config)])

        cerebro = container.get(bt.Cerebro)
        cerebro.run()
