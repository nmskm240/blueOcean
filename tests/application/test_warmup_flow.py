from __future__ import annotations

from datetime import UTC, datetime, timedelta
from queue import Queue

import backtrader as bt
import pandas as pd

from blueOcean.application.broker import Broker
from blueOcean.application.feed import QueueDataFeed
from blueOcean.application.store import IStore
from blueOcean.application.warmup import WarmupState
from blueOcean.domain.ohlcv import Ohlcv, OhlcvFetcher, Timeframe


class DummyFetcher(OhlcvFetcher):
    def __init__(self, ohlcvs: list[Ohlcv]):
        self._ohlcvs = ohlcvs

    @property
    def source(self) -> str:
        return "dummy"

    @property
    def longest_since(self) -> datetime:
        return datetime(2017, 1, 1, tzinfo=UTC)

    def _fetch_ohlcv_process(self, symbol: str, since_at: datetime):
        yield self._ohlcvs


class DummyStore(IStore):
    def __init__(self):
        super().__init__("BTC/USDT")
        self.created_orders = []

    def get_cash(self) -> float:
        return 0.0

    def get_value(self) -> float:
        return 0.0

    def get_positions(self):
        return []

    def create_order(self, order):
        self.created_orders.append(order)
        return order

    def cancel_order(self, order):
        return None

    def update_account_state(self):
        return None


def _dummy_data_feed() -> bt.feeds.PandasData:
    index = [datetime.now()]
    df = pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        },
        index=index,
    )
    return bt.feeds.PandasData(dataname=df)


def test_queue_data_feed_warmup_marks_ready_after_history():
    now = datetime.now(tz=UTC).replace(second=0, microsecond=0)
    history = [
        Ohlcv(
            time=now - timedelta(minutes=2),
            open=1,
            high=1,
            low=1,
            close=1,
            volume=1,
        ),
        Ohlcv(
            time=now - timedelta(minutes=1),
            open=2,
            high=2,
            low=2,
            close=2,
            volume=2,
        ),
    ]
    queue = Queue()
    queue.put_nowait(
        Ohlcv(
            time=now,
            open=3,
            high=3,
            low=3,
            close=3,
            volume=3,
        )
    )
    warmup_state = WarmupState()
    fetcher = DummyFetcher(history)

    feed = QueueDataFeed(
        queue=queue,
        fetcher=fetcher,
        symbol="BTC/USDT",
        ohlcv_timeframe=Timeframe.ONE_MINUTE,
        warmup_state=warmup_state,
        warmup_limit=1000,
    )
    feed.start()

    assert warmup_state.is_ready() is False

    assert feed._load() is True
    assert feed.lines.close[0] == 1
    assert warmup_state.is_ready() is False

    assert feed._load() is True
    assert feed.lines.close[0] == 2
    assert warmup_state.is_ready() is False

    assert feed._load() is True
    assert feed.lines.close[0] == 3
    assert warmup_state.is_ready() is True


def test_broker_rejects_orders_during_warmup():
    store = DummyStore()
    warmup_state = WarmupState()
    warmup_state.mark_pending()
    broker = Broker(store=store, warmup_state=warmup_state)
    data = _dummy_data_feed()

    order = broker.buy(
        owner=object(),
        data=data,
        size=1,
        exectype=bt.Order.Market,
    )

    assert order.status == bt.Order.Rejected
    assert store.created_orders == []


def test_broker_accepts_orders_after_warmup():
    store = DummyStore()
    warmup_state = WarmupState()
    warmup_state.mark_ready()
    broker = Broker(store=store, warmup_state=warmup_state)
    data = _dummy_data_feed()

    order = broker.buy(
        owner=object(),
        data=data,
        size=1,
        exectype=bt.Order.Market,
    )

    assert order.status == bt.Order.Accepted
    assert store.created_orders == [order]
