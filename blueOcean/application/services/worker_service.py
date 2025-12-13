from typing import Type

from injector import inject

from blueOcean.application.dto import BacktestConfig, BotConfig
from blueOcean.application.workers import BacktestWorker, RealTradeWorker
from blueOcean.infra.database.repositories import BotRepository


class WorkerService:
    @inject
    def __init__(self, bot_repository: BotRepository):
        self.bot_workers: dict[str, RealTradeWorker] = {}
        self.bot_repository = bot_repository

    def spawn_real_trade(self, bot_id: str, config: BotConfig) -> RealTradeWorker:
        worker = RealTradeWorker(config)

        worker.start()
        self.bot_workers[bot_id] = worker

        self.bot_repository.save(
            bot_id=bot_id,
            pid=worker.pid,
            status=BotRepository.STATUS_RUNNING,
        )

        return worker

    def stop_real_trade(self, bot_id: str):
        worker = self.bot_workers.get(bot_id)
        if not worker:
            return

        worker.terminate()
        self.bot_repository.update(
            bot_id=bot_id,
            status=BotRepository.STATUS_STOPPED,
        )
        del self.bot_workers[bot_id]

    def spawn_backtest(self, config: BacktestConfig) -> BacktestWorker:
        worker = BacktestWorker(config)
        worker.start()
        return worker
