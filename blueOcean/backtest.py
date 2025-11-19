from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Type

import backtrader as bt
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt


@dataclass
class BacktestResult:
    cerebro: bt.Cerebro
    strategy: bt.Strategy
    analyzers: Dict[str, Dict[str, Any]]
    final_value: float

    def plot(self):
        backend = plt.get_backend().lower()
        if backend != "agg":
            plt.switch_backend("Agg")
        matplotlib.rcParams["backend"] = "Agg"
        plots = self.cerebro.plot(iplot=False)
        if not plots:
            raise RuntimeError("グラフを生成できませんでした。")
        first_plot = plots[0]
        if isinstance(first_plot, list):
            figure = first_plot[0]
        else:
            figure = first_plot
        return figure


def create_sample_ohlcv(length: int = 500, seed: int | None = None) -> pd.DataFrame:
    if length <= 0:
        raise ValueError("length must be positive")

    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, size=length))
    open_prices = close + rng.normal(0, 0.2, size=length)
    high = np.maximum(open_prices, close) + np.abs(rng.normal(0, 0.3, size=length))
    low = np.minimum(open_prices, close) - np.abs(rng.normal(0, 0.3, size=length))
    volume = rng.integers(100, 1000, size=length)

    index = pd.date_range(end=pd.Timestamp.utcnow(), periods=length, freq="h")
    df = pd.DataFrame(
        {
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "openinterest": np.zeros(length),
        },
        index=index,
    )
    return df


def run_backtest(
    strategy_cls: Type[bt.Strategy],
    ohlcv: pd.DataFrame,
    *,
    cash: float = 100_000,
    commission: float = 0.001,
    **strategy_params: Any,
) -> BacktestResult:
    prepared = prepare_ohlcv_dataframe(ohlcv)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=commission)

    cerebro.addstrategy(strategy_cls, **strategy_params)

    feed = bt.feeds.PandasData(dataname=prepared)
    cerebro.adddata(feed)

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)

    strategies = cerebro.run()
    strategy = strategies[0]
    analyzers = {
        "trade": strategy.analyzers.trade.get_analysis(),
        "sharpe": strategy.analyzers.sharpe.get_analysis(),
    }
    final_value = cerebro.broker.getvalue()

    return BacktestResult(
        cerebro=cerebro,
        strategy=strategy,
        analyzers=analyzers,
        final_value=final_value,
    )


def prepare_ohlcv_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be DatetimeIndex")

    lower_map = {col.lower(): col for col in df.columns}
    required = ["open", "high", "low", "close", "volume"]
    missing = [col for col in required if col not in lower_map]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    rename_map = {lower_map[col]: col for col in required}
    normalized = df.rename(columns=rename_map).copy()

    openinterest_source = next(
        (col for col in normalized.columns if col.lower() == "openinterest"),
        None,
    )
    if openinterest_source and openinterest_source != "openinterest":
        normalized = normalized.rename(columns={openinterest_source: "openinterest"})
    elif openinterest_source is None:
        normalized["openinterest"] = 0.0

    normalized = normalized.sort_index()
    return normalized[["open", "high", "low", "close", "volume", "openinterest"]]
