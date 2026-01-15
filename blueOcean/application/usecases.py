from __future__ import annotations

from injector import inject
from datetime import datetime

from blueOcean.application.accessors import IBotRuntimeDirectoryAccessor
from blueOcean.application.dto import BotInfo, IBotConfig, TimeReturnPoint
from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.application.mapper import to_bot_info
from blueOcean.application.services import BotExecutionService, IExchangeService
from blueOcean.domain.bot import BotId, IBotRepository
from blueOcean.domain.ohlcv import IOhlcvRepository


class FetchOhlcvUsecase:
    @inject
    def __init__(
        self,
        fetcher_factory: IOhlcvFetcherFactory,
        ohlcv_repository: IOhlcvRepository,
    ):
        self._fetcher_factory = fetcher_factory
        self._ohlcv_repository = ohlcv_repository

    def execute(self, exchange_name: str, symbol: str):
        # TODO: スレッドに逃がすべきな印象
        latest_at = self._ohlcv_repository.get_latest_timestamp(
            exchange_name, symbol
        )
        fetcher = self._fetcher_factory.create(exchange_name)

        for batch in fetcher.fetch_ohlcv(symbol, latest_at):
            self._ohlcv_repository.save(batch, exchange_name, symbol)


class FetchExchangeSymbolsUsecase:
    @inject
    def __init__(self, exchange_service: IExchangeService):
        self._service = exchange_service

    def execute(self, exchange_name: str) -> list[str]:
        return self._service.symbols_for(exchange_name)


class FetchFetchableExchangesUsecase:
    @inject
    def __init__(self, exchange_service: IExchangeService):
        self._service = exchange_service

    def execute(self) -> list[str]:
        return self._service.fetchable_exchanges()


class FetchBotsUsecase:
    @inject
    def __init__(self, repository: IBotRepository):
        self._repository = repository

    def execute(self, *bot_ids: BotId) -> list[BotInfo]:
        if len(bot_ids) == 0:
            bots = self._repository.get_all()
        else:
            bots = self._repository.find_by_ids(*bot_ids)
        return [to_bot_info(bot) for bot in bots]


class FetchBotTimeReturnsUsecase:
    @inject
    def __init__(
        self,
        directory_accessor: IBotRuntimeDirectoryAccessor,
    ):
        self._accessor = directory_accessor

    def execute(self) -> list[TimeReturnPoint]:
        return [
            TimeReturnPoint(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                analyzer=str(row["analyzer"]),
                key=str(row["key"]),
                value=float(row["value"]),
            )
            for index, row in self._accessor.metrics.iterrows()
        ]


class LaunchBotUsecase:
    @inject
    def __init__(self, execution_service: BotExecutionService):
        self._execution_service = execution_service

    def execute(self, config: IBotConfig) -> BotId:
        context = config.to_context()
        return self._execution_service.start(context)
