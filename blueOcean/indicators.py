import math
import backtrader as bt


class SlopeAngle(bt.Indicator):
    """指定した期間からの傾きを求める

    lines.angle: 傾き

    params:
        period: 傾き計算に使う期間
        normalized: 正規化するか
    """

    lines = ("angle",)
    params = (
        ("period", 1),
        ("normalize", True),
    )

    def __init__(self):
        self.addminperiod(self.p.period + 1)

    def next(self):
        current = self.data[0]
        past = self.data[-self.p.period]
        delta = current - past

        if self.p.normalize and past != 0:
            slope = (delta / abs(past)) / self.p.period
        else:
            slope = delta / self.p.period

        angle_deg = math.degrees(math.atan(slope))
        self.lines.angle[0] = angle_deg


class CrossAngle(bt.Indicator):
    """交差角（なす角）を求める

    lines.angle: 交差角度（度）

    params:
        period: 傾き計算の期間
    """

    _mindatas = 2
    lines = ("angle",)
    params = dict(
        period=1,
    )

    def __init__(self):
        self.addminperiod(self.p.period + 1)

    def nextstart(self):
        self.lines.angle[0] = math.nan

    def next(self):
        self.lines.angle[0] = self._calc_angle(0)

    def once(self, start, end):
        for i in range(min(end, start + self.p.period)):
            self.lines.angle.array[i] = math.nan

        for i in range(start + self.p.period, end):
            self.lines.angle.array[i] = self._calc_angle(i)

    def _calc_angle(self, i: int) -> float:
        slope0 = (self.data0[i] - self.data0[i - self.p.period]) / self.p.period
        slope1 = (self.data1[i] - self.data1[i - self.p.period]) / self.p.period
        denom = 1 + slope0 * slope1
        if denom == 0:
            angle_rad = math.pi / 2
        else:
            angle_rad = math.atan(abs((slope0 - slope1) / denom))
        return math.degrees(angle_rad)

class AnyPercentR(bt.Indicator):
    lines = ('any_percent_r',)
    params = (('period', 14),)

    def __init__(self):
        highest = bt.indicators.Highest(self.data, period=self.p.period)
        lowest = bt.indicators.Lowest(self.data, period=self.p.period)
        eps = 1e-9
        self.l.any_percent_r = -100 * (highest - self.data) / (highest - lowest + eps)
