from datetime import datetime
from threading import Event
from queue import Queue

import pandas as pd

from blueOcean.strategy.adapters import YFinanceMarketDataSource
from blueOcean.strategy.models import StrategyConfig


def test_yfinance_adapter_builds_pandas_feed_from_history():
    calls = []
    index = pd.date_range(datetime(2025, 1, 1), periods=80, freq="D")
    frame = pd.DataFrame(
        {
            "Open": range(80),
            "High": range(1, 81),
            "Low": range(80),
            "Close": range(1, 81),
            "Volume": [100] * 80,
        },
        index=index,
    )

    def downloader(symbol, **kwargs):
        calls.append((symbol, kwargs))
        return frame

    config = StrategyConfig(
        name="Yahoo backtest",
        definition_key="moving_average_cross",
        account_id=None,
        symbol="AAPL",
        timeframe="D1",
        data_source="yfinance",
        execution_backend="backtest",
        history_period="1y",
    )

    feed = YFinanceMarketDataSource(downloader).create_feed(config, Event(), Queue())

    assert feed.p.dataname.equals(frame)
    assert calls == [
        (
            "AAPL",
            {
                "period": "1y",
                "interval": "1d",
                "auto_adjust": True,
                "progress": False,
            },
        )
    ]


def test_yfinance_adapter_maps_forex_pair_to_yahoo_ticker():
    assert YFinanceMarketDataSource.to_yfinance_symbol("EURUSD") == "EURUSD=X"
    assert YFinanceMarketDataSource.to_yfinance_symbol("AAPL") == "AAPL"
    assert YFinanceMarketDataSource.to_yfinance_symbol("BTC-USD") == "BTC-USD"


def test_yfinance_adapter_limits_period_for_intraday_data():
    assert YFinanceMarketDataSource.compatible_period("M1", "1y") == "5d"
    assert YFinanceMarketDataSource.compatible_period("M5", "1y") == "1mo"
    assert YFinanceMarketDataSource.compatible_period("H1", "5y") == "2y"
    assert YFinanceMarketDataSource.compatible_period("D1", "5y") == "5y"
