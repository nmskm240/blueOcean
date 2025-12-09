import threading
import time
from datetime import UTC, datetime, timedelta
from multiprocessing import Process, Queue
from multiprocessing.connection import Connection

import backtrader as bt
import ccxt

from blueOcean.infra.settings import Setting
from blueOcean.ohlcv import CcxtOhlcvFetcher


class ExchangeWorker(Process):
    def __init__(
        self,
        source: str,
        symbol: str,
        ohlcv_queue: Queue,
        order_pipe: Connection,
        account_state_pipe: Connection,
    ):
        super().__init__()
        self.ohlcv_queue = ohlcv_queue
        self.order_pipe = order_pipe
        self.account_state_pipe = account_state_pipe
        self.source = source
        self.symbol = symbol
        self.name = f"{self.source}:{self.symbol}"

        self.threads = []
        self.should_terminate = False

    def run(self):
        self.should_terminate = False

        # TODO: ccxt以外を使う場合はExchangeの抽象化とFactory化が必要
        meta: type[ccxt.Exchange] = getattr(ccxt, self.source)
        self.exchange = meta(
            {
                "apiKey": Setting.BYBIT_API_KEY,
                "secret": Setting.BYBIT_API_SECRET,
            }
        )
        self.exchange.set_sandbox_mode(True)
        self.exchange.load_markets()

        self.threads = [
            threading.Thread(name="fetcher", target=self._fetch_ohlcv, daemon=True),
            threading.Thread(name="resolver", target=self._resolve_order, daemon=True),
            threading.Thread(
                name="updater", target=self._fetch_account_state, daemon=True
            ),
        ]
        for t in self.threads:
            t.start()

        while not self.should_terminate:
            time.sleep(1)

    def terminate(self):
        self.should_terminate = True
        for t in self.threads:
            t.join()
        return super().terminate()

    def _fetch_ohlcv(self):
        # TODO: spawnモードで動くように内部でインスタンスするためFactory化する
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

    def _fetch_account_state(self):
        while not self.should_terminate:
            balance = self.exchange.fetch_balance()

            if self.account_state_pipe.poll():
                self.account_state_pipe.recv()
                self.account_state_pipe.send(balance)
            time.sleep(0.1)

    def _resolve_order(self):
        while not self.should_terminate:
            if self.order_pipe.poll():
                req = self.order_pipe.recv()
                res = self.exchange.create_order(
                    req["symbol"],
                    "market",
                    req["side"],
                    req["amount"],
                )

                self.order_pipe.send(
                    {
                        "order_ref": req["order_ref"],
                        "ccxt_order_id": res["id"],
                    }
                )
            time.sleep(0.1)
