import random

import backtrader as bt

from blueOcean.application.decorators import strategy_page
from blueOcean.infra.logging import logger


class TestRandomOrder(bt.Strategy):
    params = (
        ("order_chance", 0.1),
        ("max_size", 0.01),
        ("cooldown", 5),
    )

    def __init__(self):
        self.last_order_bar = -9999

    def next(self):
        # クールダウン中ならスキップ
        if len(self) - self.last_order_bar < self.p.cooldown:
            return

        # ランダムに発注するかどうか
        if random.random() > self.p.order_chance:
            return

        # BUY or SELL をランダムで決める
        side = random.choice(["buy", "sell"])

        # ランダムサイズ
        size = round(random.uniform(0.001, self.p.max_size), 6)

        # 注文発行
        if side == "buy":
            o = self.buy(size=size)
        else:
            o = self.sell(size=size)

        # 最終注文バー更新
        self.last_order_bar = len(self)
