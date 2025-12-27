import dataclasses

from injector import inject

from blueOcean.application.dto import AccountCredentialInfo, BacktestConfig
from blueOcean.application.usecases import (
    FetchAccountsUsecase,
    FetchFetchableExchangesUsecase,
    FetchOhlcvUsecase,
    LaunchBotUsecase,
    RegistAccountUsecase,
)
from blueOcean.presentation.states import OhlcvFetchDialogState


class BacktestNotifier:
    def __init__(self, launch_usecase: LaunchBotUsecase):
        self._state = BacktestConfig()
        self._launch_usecase = launch_usecase

    @property
    def state(self):
        return self._state

    def on_request_backtest(self):
        self._launch_usecase.execute(self._state)


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
