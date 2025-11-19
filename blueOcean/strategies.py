from __future__ import annotations
import backtrader as bt
from . import indicators
from .streamlit_pages import strategy_page


@strategy_page(title="移動平均クロス戦略", description="2本の移動平均線の交差を利用したシンプルなストラテジーです。")
class MACross(bt.Strategy):
    """短期・長期の移動平均線と交差角を利用して売買判断を行う。"""
    def __init__(self, short_length, long_length, angle_period=1, angle_threshold=15):
        if long_length <= short_length:
            raise ValueError("long_length must be greater than short_length")

        self.short_sma = bt.indicators.SMA(self.data, period=short_length)
        self.long_sma = bt.indicators.SMA(self.data, period=long_length)
        self.crossover = bt.indicators.CrossOver(self.short_sma, self.long_sma)
        self.angle = indicators.CrossAngle(self.short_sma, self.long_sma)
        self.angle_threshold = angle_threshold

    def next(self):
        if self.crossover[0] > 0:
            if self.position:
                self.close()
            if self.angle[0] >= self.angle_threshold:
                self.buy()

        elif self.crossover[0] < 0:
            if self.position:
                self.close()
            if self.angle[0] >= self.angle_threshold:
                self.sell()
