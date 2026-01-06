import dataclasses
import datetime

import ccxt
from injector import inject

from blueOcean.application.dto import (
    AccountCredentialInfo,
    BacktestConfig,
    DatetimeRange,
)
from blueOcean.application.usecases import (
    FetchAccountsUsecase,
    FetchBotsUsecase,
    FetchBotTimeReturnsUsecase,
    FetchFetchableExchangesUsecase,
    FetchOhlcvUsecase,
    LaunchBotUsecase,
    RegistAccountUsecase,
)
from blueOcean.domain.bot import BotId
from blueOcean.presentation.states import (
    AccountCredentialDialogState,
    BacktestDialogState,
    BotDetailPageState,
    BotTopPageState,
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
        if not self._state.account:
            return
        self._fetch_usecase.execute(
            self._state.account.account_id,
            self._state.symbol,
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
        self._state = AccountCredentialDialogState(
            exchange_options=sorted({*ccxt.exchanges, "oanda"}),
        )
        self._regist_usecase = regist_usecase

    @property
    def state(self) -> AccountCredentialDialogState:
        return self._state

    def update(self, **kwargs):
        self._state = dataclasses.replace(self._state, **kwargs)

    def submit(self) -> str:
        payload = self._state.drift
        res = self._regist_usecase.execute(payload)
        return res.value


class BotTopPageNotifier:
    @inject
    def __init__(self, fetch_usecase: FetchBotsUsecase):
        self._fetch_usecase = fetch_usecase
        self._state = BotTopPageState(bots=self._fetch_usecase.execute())

    @property
    def state(self) -> BotTopPageState:
        return self._state

    def update(self):
        self._state = BotTopPageState(bots=self._fetch_usecase.execute())


class BotDetailPageNotifier:
    @inject
    def __init__(
        self,
        bot_id: BotId,
        fetch_bots_usecase: FetchBotsUsecase,
        fetch_time_returns_usecase: FetchBotTimeReturnsUsecase,
    ):
        self._id = bot_id
        self._fetch_bots_usecase = fetch_bots_usecase
        self._fetch_time_returns_usecase = fetch_time_returns_usecase
        self._state = BotDetailPageState(
            info=self._fetch_bots_usecase.execute(bot_id)[0],
            time_returns=self._fetch_time_returns_usecase.execute(),
        )

    @property
    def state(self) -> BotDetailPageState:
        return self._state
