from multiprocessing import Process, Queue
from multiprocessing.connection import Connection
from typing import Type

import backtrader as bt

from blueOcean.application.broker import Broker
from blueOcean.field.service import TStrategy
from blueOcean.infra.stores import CcxtSpotStore
from blueOcean.ohlcv import QueueDataFeed


class BotWorker(Process):
    def __init__(
        self,
        symbol: str,
        ohlcv_queue: Queue,
        order_pipe: Connection,
        account_state_pipe: Connection,
        strategy_cls: Type[TStrategy],
        **strategy_args,
    ):
        super().__init__()
        # FIXME: ohlcv_queueの時点でどのシンボルかは確定しているため、
        # 別個でシンボルを渡すよりはOhlcvにsymbolを含めてFeedで確認したほうがいいかもしれない
        self.symbol = symbol
        self.ohlcv_queue = ohlcv_queue
        self.order_pipe = order_pipe
        self.account_state_pipe = account_state_pipe
        self.strategy_cls = strategy_cls
        self.strategy_args = strategy_args
        self.name = f"{strategy_cls.__name__}({strategy_args.values})"

    def run(self):
        cerebro = bt.Cerebro()
        cerebro.addstrategy(self.strategy_cls, **self.strategy_args)
        cerebro.adddata(QueueDataFeed(queue=self.ohlcv_queue, symbol=self.symbol))
        cerebro.broker = Broker(CcxtSpotStore(self.symbol, self.order_pipe, self.account_state_pipe))

        cerebro.run()
