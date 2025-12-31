import dataclasses
import datetime

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
    FetchPlaygroundNotebooksUsecase,
    FetchPlaygroundRunDetailUsecase,
    FetchPlaygroundRunsUsecase,
    ExecutePlaygroundNotebookUsecase,
    InspectPlaygroundNotebookParametersUsecase,
    LaunchBotUsecase,
    RegistAccountUsecase,
)
from blueOcean.domain.bot import BotId
from blueOcean.presentation.states import (
    BacktestDialogState,
    BotDetailPageState,
    BotTopPageState,
    OhlcvFetchDialogState,
    PlaygroundHistoryDetailPageState,
    PlaygroundHistoryPageState,
    PlaygroundPageState,
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


class PlaygroundPageNotifier:
    @inject
    def __init__(
        self,
        fetch_notebooks_usecase: FetchPlaygroundNotebooksUsecase,
        inspect_parameters_usecase: InspectPlaygroundNotebookParametersUsecase,
        execute_usecase: ExecutePlaygroundNotebookUsecase,
    ):
        self._fetch_notebooks_usecase = fetch_notebooks_usecase
        self._inspect_parameters_usecase = inspect_parameters_usecase
        self._execute_usecase = execute_usecase

        notebooks = self._fetch_notebooks_usecase.execute()
        self._state = PlaygroundPageState(
            notebooks=notebooks,
            selected_notebook=notebooks[0] if notebooks else None,
        )

    @property
    def state(self) -> PlaygroundPageState:
        return self._state

    def update(self, **kwargs) -> None:
        self._state = dataclasses.replace(self._state, **kwargs)

    def refresh_notebooks(self) -> None:
        notebooks = self._fetch_notebooks_usecase.execute()
        selected = self._state.selected_notebook
        if selected not in notebooks:
            selected = notebooks[0] if notebooks else None
        self._state = dataclasses.replace(
            self._state,
            notebooks=notebooks,
            selected_notebook=selected,
        )

    def select_notebook(self, notebook_name: str | None) -> None:
        if not notebook_name:
            self.update(selected_notebook=None, parameters=[], parameter_values={})
            return
        parameters = self._inspect_parameters_usecase.execute(notebook_name)
        values = {
            param.name: str(param.default) if param.default is not None else \"\"
            for param in parameters
        }
        self.update(
            selected_notebook=notebook_name,
            parameters=parameters,
            parameter_values=values,
            error_message=None,
        )

    def execute(self) -> PlaygroundPageState:
        if not self._state.selected_notebook:
            self.update(error_message=\"ノートブックが選択されていません。\")
            return self._state
        parameters = {
            key: self._parse_value(value)
            for key, value in self._state.parameter_values.items()
        }
        self.update(is_loading=True, error_message=None)
        run_info = self._execute_usecase.execute(
            self._state.selected_notebook, parameters
        )
        self.update(
            markdown=run_info.markdown,
            is_loading=False,
        )
        return self._state

    @staticmethod
    def _parse_value(value: str) -> object:
        if value == \"\":
            return None
        for caster in (int, float):
            try:
                return caster(value)
            except ValueError:
                continue
        if value.lower() in {\"true\", \"false\"}:
            return value.lower() == \"true\"
        return value


class PlaygroundHistoryPageNotifier:
    @inject
    def __init__(self, fetch_runs_usecase: FetchPlaygroundRunsUsecase):
        self._fetch_runs_usecase = fetch_runs_usecase
        self._state = PlaygroundHistoryPageState(runs=self._fetch_runs_usecase.execute())

    @property
    def state(self) -> PlaygroundHistoryPageState:
        return self._state

    def refresh(self) -> None:
        self._state = PlaygroundHistoryPageState(runs=self._fetch_runs_usecase.execute())


class PlaygroundHistoryDetailPageNotifier:
    @inject
    def __init__(self, fetch_detail_usecase: FetchPlaygroundRunDetailUsecase):
        self._fetch_detail_usecase = fetch_detail_usecase
        self._state = PlaygroundHistoryDetailPageState()

    @property
    def state(self) -> PlaygroundHistoryDetailPageState:
        return self._state

    def load(self, run_id: str) -> None:
        run = self._fetch_detail_usecase.execute(run_id)
        self._state = PlaygroundHistoryDetailPageState(run=run)
