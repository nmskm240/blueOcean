from __future__ import annotations

from injector import inject
from datetime import datetime

from blueOcean.application.accessors import IBotRuntimeDirectoryAccessor
from blueOcean.application.dto import (
    AccountCredentialInfo,
    BotInfo,
    IBotConfig,
    TimeReturnPoint,
)
from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.application.mapper import to_account, to_bot_info
from blueOcean.application.services import BotExecutionService, IExchangeService
from blueOcean.domain.account import AccountId
from blueOcean.domain.bot import BotId, IBotRepository
from blueOcean.domain.ohlcv import IOhlcvRepository
from blueOcean.infra.database.repositories import AccountRepository


class FetchOhlcvUsecase:
    @inject
    def __init__(
        self,
        fetcher_factory: IOhlcvFetcherFactory,
        ohlcv_repository: IOhlcvRepository,
        account_repository: AccountRepository,
    ):
        self._fetcher_factory = fetcher_factory
        self._ohlcv_repository = ohlcv_repository
        self._account_repository = account_repository

    def execute(self, account_id: AccountId, symbol: str):
        # TODO: スレッドに逃がすべきな印象
        account = self._account_repository.find_by_id(account_id)
        latest_at = self._ohlcv_repository.get_latest_timestamp(
            account.credential.exchange, symbol
        )
        fetcher = self._fetcher_factory.create(account_id)

        for batch in fetcher.fetch_ohlcv(symbol, latest_at):
            self._ohlcv_repository.save(batch, account.credential.exchange, symbol)


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


class RegistAccountUsecase:
    @inject
    def __init__(self, repository: AccountRepository):
        self._repository = repository

    def execute(self, request: AccountCredentialInfo) -> AccountId:
        account = to_account(request)

        saved = self._repository.save(account)
        return saved.id


class FetchAccountsUsecase:
    @inject
    def __init__(self, repository: AccountRepository):
        self._repository = repository

    def execute(self):
        accounts = self._repository.get_all()
        return [
            AccountCredentialInfo(
                account_id=account.id.value,
                exchange_name=account.credential.exchange,
                api_key=account.credential.key,
                api_secret=account.credential.secret,
                is_sandbox=account.credential.is_sandbox,
            )
            for account in accounts
        ]


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
