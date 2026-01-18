import dataclasses
import datetime

from injector import inject

from blueOcean.application.usecases import (
    FetchFetchableExchangesUsecase,
    FetchOhlcvUsecase,
    FetchSessionContextsUsecase,
    FetchSessionsUsecase,
    LaunchBacktestSessionUsecase,
)
from blueOcean.presentation.states import (
    BacktestDialogState,
    OhlcvFetchDialogState,
    SessionDetailPageState,
    SessionTopPageState,
)


class BacktestDialogNotifier:
    @inject
    def __init__(self, launch_usecase: LaunchBacktestSessionUsecase):
        self._state = BacktestDialogState()
        self._launch_usecase = launch_usecase

    @property
    def state(self):
        return self._state

    def update(self, **kwargs):
        self._state = dataclasses.replace(self._state, **kwargs)

    def on_request_backtest(self):
        start_at, end_at = self._build_time_range()
        if not self._state.strategy:
            return
        self._launch_usecase.execute(
            source=self._state.source,
            symbol=self._state.symbol,
            timeframe=self._state.timeframe,
            strategy_name=self._state.strategy,
            strategy_args=self._state.strategy_args,
            start_at=start_at,
            end_at=end_at,
        )

    def _build_time_range(self) -> tuple[datetime.datetime, datetime.datetime]:
        start_at = (
            datetime.datetime.combine(self._state.start_date, datetime.time.min)
            if self._state.start_date
            else datetime.datetime.min
        )
        end_at = (
            datetime.datetime.combine(self._state.end_date, datetime.time.max)
            if self._state.end_date
            else datetime.datetime.max
        )
        return start_at, end_at


class OhlcvFetchDialogNotifier:
    @inject
    def __init__(
        self,
        fetch_usecase: FetchOhlcvUsecase,
        exchanges_usecase: FetchFetchableExchangesUsecase,
    ):
        self._fetch_usecase = fetch_usecase
        self._exchanges_usecase = exchanges_usecase

        self._state = OhlcvFetchDialogState(
            exchanges=self._exchanges_usecase.execute(),
        )

    @property
    def state(self) -> OhlcvFetchDialogState:
        return self._state

    def update(self, **kwargs) -> None:
        self._state = dataclasses.replace(self._state, **kwargs)

    def submit(self) -> None:
        if not self._state.exchange:
            return
        self._fetch_usecase.execute(
            self._state.exchange,
            self._state.symbol,
        )

class SessionTopPageNotifier:
    @inject
    def __init__(self, fetch_usecase: FetchSessionsUsecase):
        self._fetch_usecase = fetch_usecase
        self._state = SessionTopPageState(sessions=self._fetch_usecase.execute())

    @property
    def state(self) -> SessionTopPageState:
        return self._state

    def update(self):
        self._state = SessionTopPageState(sessions=self._fetch_usecase.execute())


class SessionDetailPageNotifier:
    @inject
    def __init__(
        self,
        session_id: str,
        fetch_sessions_usecase: FetchSessionsUsecase,
        fetch_contexts_usecase: FetchSessionContextsUsecase,
    ):
        self._id = session_id
        self._fetch_sessions_usecase = fetch_sessions_usecase
        self._fetch_contexts_usecase = fetch_contexts_usecase
        sessions = self._fetch_sessions_usecase.execute(session_id)
        session = sessions[0] if sessions else None
        self._state = SessionDetailPageState(
            session=session,
            contexts=self._fetch_contexts_usecase.execute(session_id),
        )

    @property
    def state(self) -> SessionDetailPageState:
        return self._state
