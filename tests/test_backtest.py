import backtrader as bt
from matplotlib.figure import Figure
import pandas as pd

from blueOcean.backtest import BacktestResult, create_sample_ohlcv, run_backtest


class BuyHoldStrategy(bt.Strategy):
    def next(self):
        if not self.position:
            self.buy(size=1)


def test_create_sample_ohlcv_returns_valid_dataframe():
    df = create_sample_ohlcv(length=50, seed=42)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
    assert set(df.columns) == {"open", "high", "low", "close", "volume", "openinterest"}
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.is_monotonic_increasing


def test_run_backtest_returns_result():
    data = create_sample_ohlcv(length=80, seed=1)
    result = run_backtest(BuyHoldStrategy, data, cash=1_000, commission=0.0)
    assert isinstance(result, BacktestResult)
    assert result.final_value > 0
    assert "trade" in result.analyzers
    fig = result.plot()
    assert isinstance(fig, Figure)
