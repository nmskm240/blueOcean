from __future__ import annotations

import backtrader as bt
import pandas as pd
import math
import time
from datetime import datetime, timezone

from blueOcean.strategy.events import RunnerEvent
from blueOcean.strategy.models import StrategyConfig


class SyntheticLiveData(bt.feed.DataBase):
    params = (("stop_event", None), ("status_queue", None), ("interval_seconds", 0.25))

    def __init__(self):
        super().__init__()
        self._next_at = 0.0
        self._bar_number = 0

    def islive(self):
        return True

    def haslivedata(self):
        return True

    def _load(self):
        if self.p.stop_event.is_set():
            return False
        now = time.monotonic()
        if now < self._next_at:
            time.sleep(min(0.05, self._next_at - now))
            return None
        self._next_at = now + self.p.interval_seconds
        self._bar_number += 1
        close = 100.0 + math.sin(self._bar_number / 5.0)
        timestamp = datetime.now(timezone.utc)
        self.lines.datetime[0] = bt.date2num(timestamp)
        self.lines.open[0] = close
        self.lines.high[0] = close + 0.1
        self.lines.low[0] = close - 0.1
        self.lines.close[0] = close
        self.lines.volume[0] = 1
        self.lines.openinterest[0] = 0
        self.p.status_queue.put(RunnerEvent("heartbeat", timestamp))
        return True


YFINANCE_INTERVALS = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "H1": "1h",
    "H4": "1h",
    "D1": "1d",
}

YFINANCE_PERIOD_DAYS = {
    "1d": 1,
    "5d": 5,
    "1mo": 31,
    "3mo": 93,
    "6mo": 186,
    "1y": 366,
    "2y": 732,
    "5y": 1830,
    "max": float("inf"),
}

YFINANCE_MAX_PERIODS = {
    "M1": "5d",
    "M5": "1mo",
    "M15": "1mo",
    "H1": "2y",
    "H4": "2y",
}


class SyntheticMarketDataSource:
    def create_feed(self, config: StrategyConfig, stop_event, status_queue):
        return SyntheticLiveData(stop_event=stop_event, status_queue=status_queue)


class YFinanceMarketDataSource:
    def __init__(self, downloader=None) -> None:
        self._downloader = downloader

    def create_feed(self, config: StrategyConfig, stop_event, status_queue):
        if self._downloader is None:
            import yfinance as yf

            downloader = yf.download
        else:
            downloader = self._downloader
        interval = YFINANCE_INTERVALS.get(config.timeframe)
        if interval is None:
            raise ValueError(f"yfinanceは時間足{config.timeframe}に対応していません")
        download_symbol = self.to_yfinance_symbol(config.symbol)
        period = self.compatible_period(config.timeframe, config.history_period)
        frame = downloader(
            download_symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        frame = self._normalize(frame, download_symbol)
        if config.timeframe == "H4":
            frame = frame.resample("4h").agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum",
                }
            ).dropna()
        if frame.empty:
            raise ValueError("yfinanceから価格データを取得できませんでした")
        return bt.feeds.PandasData(dataname=frame)

    @staticmethod
    def to_yfinance_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if len(normalized) == 6 and normalized.isalpha():
            return f"{normalized}=X"
        return normalized

    @staticmethod
    def compatible_period(timeframe: str, requested_period: str) -> str:
        max_period = YFINANCE_MAX_PERIODS.get(timeframe)
        if max_period is None:
            return requested_period
        requested_days = YFINANCE_PERIOD_DAYS.get(requested_period)
        if requested_days is None:
            raise ValueError(f"yfinanceで未対応の履歴期間です: {requested_period}")
        if requested_days > YFINANCE_PERIOD_DAYS[max_period]:
            return max_period
        return requested_period

    @staticmethod
    def _normalize(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if isinstance(frame.columns, pd.MultiIndex):
            if symbol in frame.columns.get_level_values(-1):
                frame = frame.xs(symbol, axis=1, level=-1)
            else:
                frame.columns = frame.columns.get_level_values(0)
        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = set(required) - set(frame.columns)
        if missing:
            raise ValueError(f"yfinanceデータに必要な列がありません: {', '.join(sorted(missing))}")
        return frame[required].dropna()


class BacktestExecutionBackend:
    def configure(self, cerebro: bt.Cerebro, config: StrategyConfig) -> None:
        cerebro.broker.setcash(config.initial_cash)
        cerebro.broker.setcommission(commission=config.commission)
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(EquityCurveAnalyzer, _name="equity_curve")

    def result(self, cerebro: bt.Cerebro, strategies: list) -> dict:
        final_value = float(cerebro.broker.getvalue())
        initial_cash = float(cerebro.broker.startingcash)
        analysis = strategies[0].analyzers.trades.get_analysis() if strategies else {}
        equity_curve = strategies[0].analyzers.equity_curve.get_analysis() if strategies else []
        total = int(analysis.get("total", {}).get("total", 0))
        peak = initial_cash
        max_drawdown_pct = 0.0
        for point in equity_curve:
            peak = max(peak, point["value"])
            if peak:
                max_drawdown_pct = max(
                    max_drawdown_pct, (peak - point["value"]) / peak * 100.0
                )
        return {
            "initial_cash": initial_cash,
            "final_value": final_value,
            "net_profit": final_value - initial_cash,
            "return_pct": ((final_value / initial_cash) - 1.0) * 100.0,
            "max_drawdown_pct": max_drawdown_pct,
            "trades": total,
            "equity_curve": _downsample(equity_curve),
        }


class PaperExecutionBackend(BacktestExecutionBackend):
    pass


class EquityCurveAnalyzer(bt.Analyzer):
    def __init__(self):
        self._points = []

    def next(self):
        timestamp = self.datas[0].datetime.datetime(0)
        self._points.append(
            {"time": timestamp.isoformat(), "value": float(self.strategy.broker.getvalue())}
        )

    def get_analysis(self):
        return self._points


def _downsample(points: list[dict], limit: int = 500) -> list[dict]:
    if len(points) <= limit:
        return points
    step = (len(points) - 1) / (limit - 1)
    return [points[round(index * step)] for index in range(limit)]


MARKET_DATA_SOURCES = {
    "synthetic": SyntheticMarketDataSource,
    "yfinance": YFinanceMarketDataSource,
}

EXECUTION_BACKENDS = {
    "paper": PaperExecutionBackend,
    "backtest": BacktestExecutionBackend,
}
