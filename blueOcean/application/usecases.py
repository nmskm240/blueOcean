from __future__ import annotations

from datetime import datetime

from injector import inject

from blueOcean.application.dto import ContextInfo, SessionInfo
from blueOcean.application.factories import IOhlcvFetcherFactory
from blueOcean.application.services import IExchangeService
from blueOcean.domain.context import Context, IContextRepository
from blueOcean.domain.ohlcv import IOhlcvRepository, Timeframe
from blueOcean.domain.session import ISessionRepository, Session, SessionId
from blueOcean.domain.strategy import IStrategySnapshotRepository, StrategySnapshot


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


class FetchSessionsUsecase:
    @inject
    def __init__(self, repository: ISessionRepository):
        self._repository = repository

    def execute(self, *session_ids: str) -> list[SessionInfo]:
        if len(session_ids) == 0:
            sessions = self._repository.get_all()
        else:
            ids = [SessionId(value=value) for value in session_ids]
            sessions = self._repository.find_by_ids(*ids)
        return [
            SessionInfo(session_id=s.id.value, name=s.name)
            for s in sessions
        ]


class FetchSessionContextsUsecase:
    @inject
    def __init__(self, repository: IContextRepository):
        self._repository = repository

    def execute(self, session_id: str) -> list[ContextInfo]:
        session_id_value = SessionId(value=session_id)
        contexts = self._repository.find_by_session_id(session_id_value)
        return [
            ContextInfo(
                context_id=c.id.value,
                session_id=session_id_value.value,
                strategy_snapshot_id=c.strategy_snapshot_id.value,
                source=c.source,
                symbol=c.symbol,
                timeframe=c.timeframe.name,
                start_at=c.start_at,
                end_at=c.end_at,
                strategy_args=c.strategy_args,
            )
            for c in contexts
        ]


class LaunchBacktestSessionUsecase:
    @inject
    def __init__(
        self,
        session_repository: ISessionRepository,
        context_repository: IContextRepository,
        snapshot_repository: IStrategySnapshotRepository,
    ):
        self._session_repository = session_repository
        self._context_repository = context_repository
        self._snapshot_repository = snapshot_repository

    def execute(
        self,
        *,
        source: str,
        symbol: str,
        timeframe: Timeframe,
        strategy_name: str,
        strategy_args: dict[str, object],
        start_at: datetime,
        end_at: datetime,
        session_name: str | None = None,
    ) -> str:
        snapshot = StrategySnapshot(name=strategy_name)
        self._snapshot_repository.save(snapshot)

        context = Context(
            strategy_snapshot_id=snapshot.id,
            strategy_args=strategy_args,
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            start_at=start_at,
            end_at=end_at,
        )
        self._context_repository.save(context)

        session = Session(name=session_name or "")
        self._session_repository.save(session)

        return session.id.value
