from multiprocessing import Pipe, Queue
from typing import Type

from blueOcean.infra.workers import BotWorker, ExchangeWorker


class WorkerService:
    def __init__(self):
        self.exchange_workers: dict[tuple[str, str], ExchangeWorker] = {}
        self.bot_workers: dict[str, BotWorker] = {}

    def get_or_create_exchange_worker(self, source: str, symbol: str) -> ExchangeWorker:
        key = (source, symbol)

        if key in self.exchange_workers:
            worker = self.exchange_workers[key]
            if worker.is_alive():
                return worker

        ohlcv_queue = Queue()
        order_pipe_parent, order_pipe_child = Pipe()
        account_pipe_parent, account_pipe_child = Pipe()

        ex = ExchangeWorker(
            source=source,
            symbol=symbol,
            ohlcv_queue=ohlcv_queue,
            order_pipe=order_pipe_child,
            account_state_pipe=account_pipe_child,
        )

        ex.start()

        self.exchange_workers[key] = ex

        return ex, ohlcv_queue, order_pipe_parent, account_pipe_parent

    def spawn_bot(
        self,
        bot_id: str,
        source: str,
        symbol: str,
        strategy_cls: Type,
        strategy_args: dict,
    ):
        (
            ex,
            ohlcv_queue,
            order_pipe_parent,
            account_pipe_parent,
        ) = self.get_or_create_exchange_worker(source, symbol)

        bot = BotWorker(
            symbol=symbol,
            ohlcv_queue=ohlcv_queue,
            order_pipe=order_pipe_parent,
            account_state_pipe=account_pipe_parent,
            strategy_cls=strategy_cls,
            **strategy_args,
        )

        bot.start()
        self.bot_workers[bot_id] = bot

        return bot
