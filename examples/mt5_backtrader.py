"""Run on Windows with a logged-in MetaTrader 5 terminal."""

import os

import backtrader as bt

from blueOcean.metatrader import MT5Store


class PrintBars(bt.Strategy):
    def next(self):
        print(self.data.datetime.datetime(0), self.data.close[0])


store = MT5Store(
    path=os.getenv("MT5_PATH"),
    login=int(os.environ["MT5_LOGIN"]) if os.getenv("MT5_LOGIN") else None,
    password=os.getenv("MT5_PASSWORD"),
    server=os.getenv("MT5_SERVER"),
)
cerebro = bt.Cerebro()
cerebro.adddata(
    store.getdata(
        dataname=os.getenv("MT5_SYMBOL", "EURUSD"),
        timeframe=bt.TimeFrame.Minutes,
        compression=1,
        history=500,
        live=True,
    )
)
cerebro.setbroker(store.getbroker(magic=20260704))
cerebro.addstrategy(PrintBars)
cerebro.run()
