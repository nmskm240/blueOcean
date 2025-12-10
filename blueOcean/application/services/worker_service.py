from typing import Type

from blueOcean.application.workers import BotWorker
from blueOcean.infra.settings import Setting


class WorkerService:
    def __init__(self):
        self.bot_workers: dict[str, BotWorker] = {}

    def spawn_bot(
        self,
        bot_id: str,
        source: str,
        symbol: str,
        strategy_cls: Type,
        strategy_args: dict,
    ):
        bot = BotWorker(
            Setting.BYBIT_API_KEY,
            Setting.BYBIT_API_SECRET,
            source,
            symbol=symbol,
            strategy_cls=strategy_cls,
            **strategy_args,
        )

        bot.start()
        self.bot_workers[bot_id] = bot

        return bot
