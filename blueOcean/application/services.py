from __future__ import annotations

from injector import inject

from blueOcean.domain.bot import (
    Bot,
    BotContext,
    BotId,
    BotRunMode,
    IBotRepository,
    IBotWorkerFactory,
)


class BotWorkerFactory(IBotWorkerFactory):
    def create(self, id: BotId, context: BotContext):
        match context.mode:
            case BotRunMode.LIVE:
                from blueOcean.application.workers import LiveTradeWorker

                worker = LiveTradeWorker(id, context)
            case BotRunMode.BACKTEST:
                from blueOcean.application.workers import BacktestWorker

                worker = BacktestWorker(id, context)
            case _:
                raise RuntimeError(f"Unsupported run mode. {context.mode}")
        return worker


class BotExecutionService:
    @inject
    def __init__(
        self,
        bot_repository: IBotRepository,
        bot_worker_factory: IBotWorkerFactory,
    ):
        self._bot_repository = bot_repository
        self._bot_worker_factory = bot_worker_factory

    def start(self, context: BotContext):
        bot = Bot.create(context)
        worker = self._bot_worker_factory.create(bot.id, context)

        bot.attach(worker)
        bot.launch()
        saved = self._bot_repository.save(bot)
        return saved.id

    def stop(self, id: BotId):
        from blueOcean.application.workers import RecoverWorker

        bot = self._bot_repository.find_by_id(id)
        worker = RecoverWorker(bot.pid)

        bot.attach(worker)
        bot.shutdown()
        self._bot_repository.save(bot)
