import threading
import time
from datetime import UTC, datetime, timedelta
from multiprocessing import Process
from queue import Queue
from typing import Type

import backtrader as bt
import ccxt

from blueOcean.application.broker import Broker
from blueOcean.application.feed import QueueDataFeed
from blueOcean.infra.fetchers import CcxtOhlcvFetcher
from blueOcean.infra.stores import CcxtSpotStore


class BotWorker(Process):
    def __init__(
        self,
        key: str,
        secret: str,
        source: str,
        symbol: str,
        strategy_cls: Type[bt.Strategy],
        **strategy_args,
    ):
        super().__init__(name=f"{strategy_cls.__name__}({strategy_args.values})")
        self.key = key
        self.secret = secret
        self.source = source
        self.symbol = symbol
        self.strategy_cls = strategy_cls
        self.strategy_args = strategy_args

        self.threads = []
        self.ohlcv_queue = Queue()
        self.should_terminate = False

    def run(self):
        self.exchange = self._setup_exchange()
        self.threads = [
            threading.Thread(name="fetcher", target=self._fetch_ohlcv, daemon=True),
        ]
        for t in self.threads:
            t.start()

        cerebro = bt.Cerebro()
        cerebro.addstrategy(self.strategy_cls, **self.strategy_args)
        cerebro.adddata(QueueDataFeed(queue=self.ohlcv_queue, symbol=self.symbol))
        cerebro.broker = Broker(CcxtSpotStore(self.exchange, self.symbol))

        cerebro.run()

    def terminate(self):
        self.should_terminate = True
        for t in self.threads:
            t.join()

        return super().terminate()

    def _setup_exchange(self) -> ccxt.Exchange:
        # TODO: ccxt以外を使う場合はExchangeの抽象化とFactory化が必要
        meta: type[ccxt.Exchange] = getattr(ccxt, self.source)
        exchange = meta(
            {
                "apiKey": self.key,
                "secret": self.secret,
            }
        )
        exchange.set_sandbox_mode(True)
        exchange.load_markets()
        return exchange

    def _fetch_ohlcv(self):
        self.fetcher = CcxtOhlcvFetcher(self.exchange)
        while not self.should_terminate:
            now = datetime.now(tz=UTC)
            next_min = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            # MEMO: since_atの時間が含まれないことを考慮するため2分前の時間でリクエストを行う
            since_at = next_min - timedelta(minutes=2)
            sleep_time = (next_min - now).total_seconds()
            time.sleep(sleep_time)

            for batch in self.fetcher.fetch_ohlcv(self.symbol, since_at=since_at):
                for ohlcv in batch:
                    if now < ohlcv.time:
                        continue
                    self.ohlcv_queue.put_nowait(ohlcv)
                    break
