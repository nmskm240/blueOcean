import dataclasses
import datetime

from injector import inject

from blueOcean.application.dto import AccountCredentialInfo, BacktestConfig, DatetimeRange
from blueOcean.application.usecases import (
    FetchAccountsUsecase,
    FetchFetchableExchangesUsecase,
    FetchOhlcvUsecase,
    LaunchBotUsecase,
    RegistAccountUsecase,
    UploadOhlcvCsvUsecase,
)
from blueOcean.presentation.states import (
    BacktestDialogState,
    OhlcvCsvUploadDialogState,
    OhlcvFetchDialogState,
)
from blueOcean.shared.registries import StrategyRegistry


class BacktestDialogNotifier:
    @inject
    def __init__(self, launch_usecase: LaunchBotUsecase):
        self._state = BacktestDialogState()
        self._launch_usecase = launch_usecase

    @property
    def state(self):
        return self._state
    
    def update(self, **kwargs):
        self._state = dataclasses.replace(self._state, **kwargs)

    def on_request_backtest(self):
        self._launch_usecase.execute(self._build_config())

    def _build_config(self) -> BacktestConfig:
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
        time_range = DatetimeRange(start_at=start_at, end_at=end_at)
        strategy_cls = (
            StrategyRegistry.resolve(self._state.strategy)
            if self._state.strategy
            else None
        )
        return BacktestConfig(
            source=self._state.source,
            symbol=self._state.symbol,
            timeframe=self._state.timeframe,
            strategy_cls=strategy_cls,
            strategy_args=self._state.strategy_args,
            time_range=time_range,
        )


class OhlcvFetchDialogNotifier:
    @inject
    def __init__(
        self,
        fetch_usecase: FetchOhlcvUsecase,
        exchanges_usecase: FetchFetchableExchangesUsecase,
        accounts_usecase: FetchAccountsUsecase,
    ):
        self._fetch_usecase = fetch_usecase
        self._exchanges_usecase = exchanges_usecase
        self._accounts_usecase = accounts_usecase

        accounts = self._accounts_usecase.execute()
        self._state = OhlcvFetchDialogState(
            accounts=accounts,
        )

    @property
    def state(self) -> OhlcvFetchDialogState:
        return self._state

    def update(self, **kwargs) -> None:
        self._state = dataclasses.replace(self._state, **kwargs)

    def submit(self) -> None:
        if not self._state.accout:
            return
        self._fetch_usecase.execute(
            self._state.accout.account_id,
            self._state.symbol,
        )


class OhlcvCsvUploadDialogNotifier:
    @inject
    def __init__(self, upload_usecase: UploadOhlcvCsvUsecase):
        self._upload_usecase = upload_usecase
        self._state = OhlcvCsvUploadDialogState()

    @property
    def state(self) -> OhlcvCsvUploadDialogState:
        return self._state

    def update(self, **kwargs) -> None:
        self._state = dataclasses.replace(self._state, **kwargs)

    def submit(self) -> None:
        if not self._state.exchange or not self._state.symbol or not self._state.file_path:
            return
        self._upload_usecase.execute(
            self._state.exchange,
            self._state.symbol,
            self._state.file_path,
        )


class AccountPageNotifier:
    @inject
    def __init__(self, fetch_usecase: FetchAccountsUsecase):
        self._fetch_usecase = fetch_usecase
        self._state = self._fetch_usecase.execute()

    @property
    def state(self):
        return tuple(self._state)

    def update(self):
        self._state = self._fetch_usecase.execute()


class AccountCredentialDialogNotifier:
    @inject
    def __init__(self, regist_usecase: RegistAccountUsecase):
        # TODO: StateとDTOを分ける
        self._state = AccountCredentialInfo()
        self._regist_usecase = regist_usecase

    @property
    def state(self):
        return self._state

    def update(self, **kwargs):
        self._state = dataclasses.replace(self._state, **kwargs)

    def submit(self) -> str:
        res = self._regist_usecase.execute(self._state)
        return res.value
