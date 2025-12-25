import dataclasses
from dataclasses import replace
from datetime import datetime
from types import MappingProxyType
from typing import Callable, Type

from injector import inject

from blueOcean.application import usecases
from blueOcean.application.dto import AccountCredentialInfo, BacktestConfig
from blueOcean.application.usecases import FetchAccountsUsecase, RegistAccountUsecase
from blueOcean.domain.ohlcv import Timeframe


class BacktestNotifier:
    def __init__(self):
        self._state = BacktestConfig()

    @property
    def source(self):
        return self._state.source

    @source.setter
    def source(self, source: str):
        self._state.source = source

    @property
    def symbol(self):
        return self._state.symbol

    @symbol.setter
    def symbol(self, symbol: str):
        self._state.symbol = symbol

    @property
    def timeframe(self):
        return self._state.timeframe

    @timeframe.setter
    def timeframe(self, timeframe: Timeframe):
        self._state.timeframe = timeframe

    @property
    def strategy_cls(self):
        return self._state.strategy_cls

    @strategy_cls.setter
    def strategy_cls(self, strategy_cls: Type):
        self._state.strategy_cls = strategy_cls

    @property
    def strategy_args(self):
        return MappingProxyType(self._state.strategy_args)

    @strategy_args.setter
    def strategy_args(self, strategy_args: dict):
        self._state.strategy_args = strategy_args

    @property
    def start_at(self):
        return self._state.time_range.start_at

    @start_at.setter
    def start_at(self, start_at: datetime):
        self._state.time_range = replace(self._state.time_range, start_at=start_at)

    @property
    def end_at(self):
        return self._state.time_range.end_at

    @end_at.setter
    def end_at(self, end_at: datetime):
        self._state.time_range = replace(self._state.time_range, end_at=end_at)

    def on_request_backtest(self):
        usecases.run_bot(self._state)


class FetcherSettingNotifier:
    def __init__(
        self,
        on_update_symbols: Callable[[], list[str]] | None = None,
    ):
        self._exchange = ""
        self._symbol = ""
        self._on_update_symbols = on_update_symbols

    @property
    def exchange(self) -> str:
        return self._exchange

    @exchange.setter
    def exchange(self, exchange: str) -> None:
        self._exchange = exchange
        self._symbol = ""

        if not self._on_update_symbols is None:
            self._on_update_symbols([])

        symbols = usecases.list_exchange_symbols(exchange)
        self._symbol = symbols[0]

        if not self._on_update_symbols is None:
            self._on_update_symbols(symbols)

    @property
    def symbol(self) -> str:
        return self._symbol

    @symbol.setter
    def symbol(self, symbol: str) -> None:
        self._symbol = symbol

    def submit(self) -> None:
        usecases.fetch_ohlcv(self._exchange, self._symbol)


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
